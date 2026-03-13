from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class ProductTemplate(models.Model):
    # _name = 'afg.product.template'
    _inherit = "product.template"
    _description = "Product"

    from_date = fields.Datetime(string="From Date")
    to_date = fields.Datetime(string="To Date")

    brand_name = fields.Char(string="Brand name")
    default_vendor_id = fields.Many2one(
        "res.partner",
        string="Default Vendor",
        compute="_compute_default_vendor",
        store=True
    )
    onhand_valuation_value = fields.Float(
        string="On Hand Total Value",
        compute="_compute_onhand_valuation_value",
        store=True
    )

    year_sold_units = fields.Float(
        string="Sold Units (365 Days)",
        compute="_compute_sales_for_period",
        store=True
    )

    year_sold_value = fields.Float(
        string="Sold Value (365 Days)",
        compute="_compute_sales_for_period",
        store=True
    )

    weekly_sold_units = fields.Float(
        string="Weekly Sold Units",
        compute="_compute_sales_for_period",
        store=True
    )

    weekly_sold_value = fields.Float(
        string="Weekly Sold Value",
        compute="_compute_sales_for_period",
        store=True
    )

    @api.onchange('from_date')
    def _onchange_from_date(self):
        if self.from_date:
            # For example, keep a 7-day period
            self.to_date = self.from_date + timedelta(days=7)

    def update_compute_sales(self):
        from_date = self.from_date
        to_date = self.to_date

        all_products = self.env['product.template'].search([])
        for product in all_products:
            # pass from_date / to_date to compute_sales
            product._compute_sales_for_period(from_date, to_date)
        # return self.env.ref('afg_stock_move_tracking_log.product_export_xlsx').report_action(all_products)

    def action_open_sales_popup(self):
        for rec in self:
            today = fields.Datetime.now()
            week_date = today - timedelta(days=7)

            rec.write({
                'from_date': week_date,
                'to_date': today
            })

            return {
                'name': 'Product Report Period',
                'type': 'ir.actions.act_window',
                'res_model': 'product.template',
                'view_mode': 'form',
                'view_id': rec.env.ref('afg_stock_move_tracking_log.view_product_sales_popup').id,
                'res_id': rec[0].id,
                'target': 'new',
            }

    def _compute_sales_for_period(self, from_date=None, to_date=None):
        SaleLine = self.env['sale.order.line']
        today = fields.Datetime.now()
        year_date = today - timedelta(days=365)
        from_date = from_date or (today - timedelta(days=7))
        to_date = to_date or today

        # Prepare mapping for all variants
        product_variant_ids = self.mapped('product_variant_ids.id')
        if not product_variant_ids:
            for template in self:
                template.year_sold_units = 0
                template.year_sold_value = 0
                template.weekly_sold_units = 0
                template.weekly_sold_value = 0
            return

        # YEAR SALES: compute for all variants at once
        year_data = SaleLine.read_group(
            [('product_id', 'in', product_variant_ids),
             ('order_id.state', 'in', ['sale', 'done']),
             ('order_id.date_order', '>=', year_date)],
            ['product_id', 'product_uom_qty:sum', 'price_total:sum'],
            ['product_id']
        )
        year_map = {row['product_id'][0]: row for row in year_data}

        # WEEK / selected period sales
        week_data = SaleLine.read_group(
            [('product_id', 'in', product_variant_ids),
             ('order_id.state', 'in', ['sale', 'done']),
             ('order_id.date_order', '>=', from_date),
             ('order_id.date_order', '<=', to_date)],
            ['product_id', 'product_uom_qty:sum', 'price_total:sum'],
            ['product_id']
        )
        week_map = {row['product_id'][0]: row for row in week_data}

        # Assign values to each template
        for template in self:
            variant_ids = template.product_variant_ids.ids

            # YEAR
            year_units = sum(year_map[v]['product_uom_qty'] for v in variant_ids if v in year_map)
            year_value = sum(year_map[v]['price_total'] for v in variant_ids if v in year_map)
            template.year_sold_units = year_units
            template.year_sold_value = year_value

            # WEEK / selected period
            week_units = sum(week_map[v]['product_uom_qty'] for v in variant_ids if v in week_map)
            week_value = sum(week_map[v]['price_total'] for v in variant_ids if v in week_map)
            template.weekly_sold_units = week_units
            template.weekly_sold_value = week_value

    def update_weekly_compute_sales(self):


        SaleLine = self.env['sale.order.line']

        for template in self:
            today = fields.Datetime.now()
            from_date = (fields.Datetime.now() - timedelta(days=7))
            to_date = fields.Datetime.now()
            year_date = today - timedelta(days=365)
            variant_ids = template.product_variant_ids.ids

            # YEAR SALES
            year_data = SaleLine.read_group(
                [
                    ('product_id', 'in', variant_ids),
                    ('order_id.state', 'in', ['sale', 'done']),
                    ('order_id.date_order', '>=', year_date)
                ],
                ['product_uom_qty:sum', 'price_total:sum'],
                []
            )

            template.year_sold_units = year_data[0]['product_uom_qty'] if year_data else 0
            template.year_sold_value = year_data[0]['price_total'] if year_data else 0

            # WEEK SALES
            week_data = SaleLine.read_group(
                [
                    ('product_id', 'in', variant_ids),
                    ('order_id.state', 'in', ['sale', 'done']),
                    ('order_id.date_order', '>=', from_date),
                    ('order_id.date_order', '<=', to_date)
                ],
                ['product_uom_qty:sum', 'price_total:sum'],
                []
            )

            template.weekly_sold_units = week_data[0]['product_uom_qty'] if week_data else 0
            template.weekly_sold_value = week_data[0]['price_total'] if week_data else 0

    @api.depends("product_variant_ids.stock_valuation_layer_ids")
    def _compute_onhand_valuation_value(self):
        for record in self:
            layers = self.env["stock.valuation.layer"].search([
                ("product_id.product_tmpl_id", "=", record.id)
            ])

            total_value = sum(layers.mapped("remaining_value"))
            record.onhand_valuation_value = total_value

    @api.depends("seller_ids")
    def _compute_default_vendor(self):
        for record in self:
            first_seller = record.seller_ids[:1]
            record.default_vendor_id = first_seller.partner_id if first_seller else False