from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class PurchaseOrderLine(models.Model):
    # _name = 'afg.product.template'
    _inherit = "purchase.order.line"
    _description = "Purchase Order Line"

    DEFAULT_UOM_PRIORITY = ['g', 'dozens', 'cm', 'mm', 'pieces', 'ft²', 'in³', 'unit', 'kg', 'sqmt', ]
    os_po_qty_new = fields.Float(string="O/S Purchased Units",
                                 compute="_compute_os_po_qty",
                                 store=True
                                 )
    report_pro_id = fields.Many2one('product.template', string="Product")
    os_po_value = fields.Float(
        string="Outstanding PO Value",
        compute="_compute_os_po_value",
        store=True
    )

    conversion_uom = fields.Many2one(
        'uom.uom',
        string="Conversion UoM",
        domain="[('category_id', '=', product_uom_category_id), ('id', '=', product_uom)]"
    )

    converted_qty = fields.Float(
        string="Converted Quantity",
        compute="_compute_converted_qty",
        store=True
    )

    @api.depends('product_qty', 'product_uom', 'conversion_uom')
    def _compute_converted_qty(self):
        for line in self:
            if line.product_uom and line.conversion_uom:
                line.converted_qty = line.product_uom._compute_quantity(
                    line.product_qty,
                    line.conversion_uom
                )
            else:
                line.converted_qty = 0.0

    # @api.onchange('product_uom')
    # def _onchange_product_uom(self):
    #     if self.product_uom:
    #         uom = self.env['uom.uom'].search([
    #             ('category_id', '=', self.product_uom.category_id.id),
    #             ('id', '=', self..id)
    #         ], limit=1)
    #         self.conversion_uom = uom

    @api.depends('product_uom_qty', 'qty_received')
    def _compute_os_po_qty(self):
        for rec in self:
            rec.os_po_qty_new = rec.product_uom_qty - rec.qty_received

    @api.depends('os_po_qty_new', 'price_unit')
    def _compute_os_po_value(self):
        for rec in self:
            rec.os_po_value = rec.os_po_qty_new * rec.price_unit

    @api.onchange('product_id')
    def _onchange_product_id_update_uoms(self):
        for line in self:
            if not line.product_id:
                continue

            product = line.product_id
            main_uom = product.product_tmpl_id.uom_id
            line.product_uom = main_uom


            category_id = main_uom.category_id.id
            line.conversion_uom = main_uom


    @api.model
    def create(self, vals):
        # Auto-fill conversion_uom if not provided
        if vals.get('product_id') and not vals.get('conversion_uom'):
            product = self.env['product.product'].browse(vals['product_id'])
            if product.product_tmpl_id.uom_id:
                category_id = product.product_tmpl_id.uom_id.category_id.id

                default_uom = product.product_tmpl_id.uom_id.id

                if default_uom:
                    vals['conversion_uom'] = default_uom

        # Create the line
        line = super().create(vals)

        # Compute converted_qty immediately
        if line.product_uom and line.conversion_uom:
            line.converted_qty = line.product_uom._compute_quantity(
                line.product_qty,
                line.conversion_uom
            )

        return line
