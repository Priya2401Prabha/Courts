# -*- coding: utf-8 -*-

from collections import defaultdict
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round
from odoo.addons.stock_landed_costs.models.stock_landed_cost import SPLIT_METHOD

# Prevent duplicate split method registration
if ("by_percentage", "By Percentage") not in SPLIT_METHOD:
    SPLIT_METHOD.append(("by_percentage", "By Percentage"))


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    currency_exchange_rate = fields.Float(string="Currency Exchange Rate", default=1.0)

    state = fields.Selection(
        selection_add=[
            ("approval", "Pending Approval"),
            ("reject", "Rejected"),
            ("approved", "Approved"),
        ]
    )

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    company_currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        default=lambda self: self.env.user,
    )

    insurance_amount = fields.Float(
        string="Insurance Amount (%)",
        digits="Product Price",
        default=0.1225,
    )

    amount_total_comp_currency = fields.Float(
        string="Total",
        compute="_compute_amount_total_comp_currency",
        readonly=True,
    )

    post_date = fields.Date(
        string="Posted Date",
        readonly=True,
        copy=False,
        tracking=True,
    )

    cost_valuation_lines = fields.One2many(
        "cost.valuation.lines",
        "cost_id",
        string="Cost Valuation Lines",
        copy=True,
        readonly=False,
    )

    # --------------------------------------------------
    # COMPUTES / ONCHANGE
    # --------------------------------------------------

    @api.depends("cost_lines.price_unit")
    def _compute_amount_total_comp_currency(self):
        for cost in self:
            cost.amount_total_comp_currency = cost.amount_total

    @api.onchange("account_journal_id")
    def _onchange_account_journal_id(self):
        if self.account_journal_id and self.account_journal_id.currency_id:
            self.currency_id = self.account_journal_id.currency_id

    @api.onchange("currency_id", "currency_exchange_rate")
    def _onchange_currency_id(self):
        if self.cost_lines:
            self.cost_lines._onchange_currency_price_unit()

    # --------------------------------------------------
    # ORM OVERRIDE
    # --------------------------------------------------

    def write(self, vals):
        if "picking_ids" in vals:
            self.env["cost.valuation.lines"].search([
                ("cost_id", "in", self.ids)
            ]).unlink()

            self.env["stock.valuation.adjustment.lines"].search([
                ("cost_id", "in", self.ids)
            ]).unlink()

        return super().write(vals)

    # --------------------------------------------------
    # APPROVAL FLOW
    # --------------------------------------------------

    def button_approval(self):
        template = self.env.ref(
            "afg_stock_landed_cost.send_landed_cost_approval_mail",
            raise_if_not_found=False,
        )
        group = self.env.ref(
            "afg_stock_landed_cost.landed_cost_manager",
            raise_if_not_found=False,
        )

        email_to = ",".join(
            u.email for u in group.users if u.email and u.id != 2
        ) if group else ""

        for rec in self:
            if template:
                template.subject = _("Landed Cost Approval for %s") % rec.name
                template.email_to = email_to
                template.send_mail(rec.id, force_send=True)

        self.write({"state": "approval"})

    def button_approved(self):
        template = self.env.ref(
            "afg_stock_landed_cost.send_landed_cost_approved_mail",
            raise_if_not_found=False,
        )
        for rec in self:
            if template:
                template.send_mail(rec.id, force_send=True)
        self.write({"state": "approved"})

    def button_reject(self):
        template = self.env.ref(
            "afg_stock_landed_cost.send_landed_cost_reject_mail",
            raise_if_not_found=False,
        )
        for rec in self:
            if template:
                template.send_mail(rec.id, force_send=True)
        self.write({"state": "reject"})

    def button_draft(self):
        self.write({"state": "draft"})

    # --------------------------------------------------
    # LANDED COST LOGIC
    # --------------------------------------------------

    def get_valuation_lines(self):
        self.ensure_one()
        lines = []

        for move in self._get_targeted_move_ids():
            if (
                    move.product_id.cost_method not in ("fifo", "average")
                    or move.state == "cancel"
                    or not move.product_qty
            ):
                continue

            vals = {
                "product_id": move.product_id.id,
                "move_id": move.id,
                "quantity": move.product_qty,
                "purchase_line_id": move.purchase_line_id.id,
                "purchase_currency_id": move.purchase_line_id.currency_id.id,
                "purchase_cost": move.purchase_line_id.price_unit,
                "unit_cost": sum(move.stock_valuation_layer_ids.mapped("unit_cost")),
                "former_cost": sum(move.stock_valuation_layer_ids.mapped("value")),
                "weight": move.product_id.weight * move.product_qty,
                "volume": move.product_id.volume * move.product_qty,
                "cost_id": self.id,
            }

            if not self.env["cost.valuation.lines"].search([
                ("cost_id", "=", self.id),
                ("product_id", "=", move.product_id.id),
            ]):
                self.env["cost.valuation.lines"].create(vals)

            lines.append(vals)

        if not lines:
            raise UserError(_(
                "You cannot apply landed costs to the selected records."
            ))
        return lines

    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        # AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()

        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):
            rounding = cost.currency_id.rounding
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                currency_convert_value = 0.0
                purchase_casting_us = 0.0
                po_line_id = self.env['purchase.order.line'].browse(val_line_values.get('purchase_line_id'))
                # Based on standard currency conversion rate
                # date = po_line_id.order_id.date_approve
                company = self.company_id
                # if po_line_id.currency_id != company.currency_id:
                #     currency_convert_value = po_line_id.currency_id._convert(
                #         val_line_values.get('purchase_cost'), company.currency_id, company, date
                #     )
                #     purchase_casting_us = po_line_id.currency_id._convert(
                #         po_line_id.price_subtotal, company.currency_id, company, date
                #     )
                if po_line_id.currency_id != company.currency_id:
                    currency_convert_value = val_line_values.get('purchase_cost') * self.currency_exchange_rate
                    purchase_casting_us = po_line_id.price_subtotal * self.currency_exchange_rate
                else:
                    purchase_casting_us = po_line_id.price_subtotal
                for cost_line in cost.cost_lines:
                    val_line_values.update(
                        {'cost_id': cost.id, 'cost_line_id': cost_line.id, 'unit_cost': currency_convert_value,
                         'purchase_casting_us': purchase_casting_us})
                    if not AdjustementLines.search([('cost_id', '=', cost.id), ('cost_line_id', '=', cost_line.id),
                                                    ('product_id', '=', val_line_values.get('product_id'))]):
                        self.env['stock.valuation.adjustment.lines'].create(val_line_values)
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('weight', 0.0)
                total_volume += val_line_values.get('volume', 0.0)

                unit_cost = val_line_values.get('unit_cost', 0.0)
                former_cost = val_line_values.get('former_cost', 0.0)
                # round this because former_cost on the valuation lines is also rounded
                total_cost += cost.currency_id.round(former_cost)

                total_line += 1
            total_percentage = 0.0
            for line in cost.cost_lines:
                value_split = 0.0
                total_charge = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    currency_convert_total_value = 0.0
                    currency_convert_value = 0.0
                    order_amount_total = 0.0
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if line.split_method == 'by_quantity' and total_qty:
                            # per_unit = (line.price_unit / total_qty)
                            # value = valuation.quantity * per_unit

                            company = cost.company_id
                            total_value = valuation.quantity * valuation.purchase_line_id.price_unit
                            # Based on standard currency conversion rate
                            # date = valuation.purchase_line_id.order_id.date_approve
                            # if valuation.purchase_line_id.currency_id != company.currency_id:
                            #     currency_convert_value = valuation.purchase_line_id.currency_id._convert(
                            #         total_value, company.currency_id, company, date
                            #     )
                            #     currency_convert_total_value = valuation.purchase_line_id.currency_id._convert(
                            #         valuation.purchase_line_id.order_id.amount_total, company.currency_id, company, date
                            #     )
                            if valuation.purchase_line_id.currency_id != company.currency_id:
                                currency_convert_value = total_value * self.currency_exchange_rate
                                currency_convert_total_value = valuation.purchase_line_id.order_id.amount_total * self.currency_exchange_rate
                                if currency_convert_total_value > 0.0:
                                    value = (
                                                        currency_convert_value / currency_convert_total_value or 1.0) * line.price_unit
                            else:
                                value = total_value
                            # value = valuation.quantity * per_unit
                            total_percentage += value
                        elif line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            # value = valuation.weight * per_unit
                            value = valuation.weight * per_unit
                            total_percentage += value
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                            total_percentage += value
                        elif line.split_method == 'equal':
                            value = (line.price_unit / total_line)
                            total_percentage += value
                        elif line.split_method == 'by_current_cost_price' and 'duty' in line.product_id.name.lower():
                            continue
                        elif line.split_method == 'by_current_cost_price' and total_cost and 'duty' not in line.product_id.name.lower():
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                            total_percentage += value
                        elif line.split_method == 'by_percentage' and total_qty:
                            continue
                        else:
                            value = (line.price_unit / total_line)
                            total_percentage += value

                        if rounding:
                            value = tools.float_round(value, precision_rounding=rounding, rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value
                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
                        cost_lines_id = self.env['cost.valuation.lines'].search(
                            [('product_id', '=', valuation.product_id.id)])
                        if 'freight' in line.product_id.name.lower():
                            cost_lines_id.write({'freight_charge_amount': value})
                        elif 'local' in line.product_id.name.lower():
                            cost_lines_id.write({'local_charge_amount': value})
                        elif 'fumigation' in line.product_id.name.lower():
                            cost_lines_id.write({'fumigation_charge_amount': value})
                        elif 'others' in line.product_id.name.lower():
                            cost_lines_id.write({'others_charge_amount': value})
                        elif not 'insurance' in line.product_id.name.lower():
                            cost_lines_id.write({'insurance_charge_amount': 0.0})
                        elif 'duty' in line.product_id.name.lower():
                            continue
                        else:
                            continue

        for key, value in towrite_dict.items():
            AdjustementLines.browse(key).write({'additional_landed_cost': value})
        message_id = self.env['message.wizard'].sudo().search([('id', '=', 1)])
        if not message_id:
            message_id = self.env['message.wizard'].sudo().create({'message': _("Computation is successfully done")})
        return {
            'name': _('Computed Successfully'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'message.wizard',
            # pass the id
            'res_id': message_id.id,
            'target': 'new'
        }
        # return True

    def compute_insurance_new(self):
        for rec in self:
            rec.cost_valuation_lines.compute_insurance_new()


    def compute_insurance_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        costLines = self.cost_lines.filtered(lambda l: l.split_method == "by_percentage")
        product_summary_dict = {}
        l_ids = []
        total_insurance = 0.0
        if self.insurance_amount > 0.0 and costLines:
            for line in self.valuation_adjustment_lines:
                if line.cost_line_id.split_method == 'by_percentage':
                    l_ids.append(line.id)
                if line.product_id.id not in product_summary_dict:
                    total_landed_cost = line.additional_landed_cost
                    product_summary_dict.update({line.product_id.id: total_landed_cost + line.purchase_casting_us})
                else:
                    total_landed_cost += line.additional_landed_cost
                    product_summary_dict.update({line.product_id.id: total_landed_cost + line.purchase_casting_us})
            for l_id in l_ids:
                line_id = AdjustementLines.browse(l_id)
                cost_lines_id = self.env['cost.valuation.lines'].search([('product_id', '=', line_id.product_id.id)])
                for p_id, p_info in product_summary_dict.items():
                    if line_id.product_id.id == p_id:
                        percent_amount = (p_info * self.insurance_amount) / 100
                        total_insurance += percent_amount
                        line_id.write({'additional_landed_cost': percent_amount})
                        if 'insurance' in line_id.cost_line_id.product_id.name.lower():
                            cost_lines_id.write({'insurance_charge_amount': percent_amount})
            total_insurance_amount = float_round(total_insurance, precision_digits=price_unit_prec)
            if self.currency_id != self.company_id.currency_id:
                currency_convert_value = total_insurance / (self.currency_exchange_rate or 1.0)
            else:
                currency_convert_value = float_round(total_insurance, precision_digits=price_unit_prec)
            costLines.write({'price_unit': total_insurance_amount, 'currency_price_unit': currency_convert_value})
        else:
            raise UserError(
                _("Split method for atleast on of the selected product must be 'By Percentage'\n or\n Insurance amount (%) can't be zero"))
        return True

    # --------------------------------------------------
    # VALIDATION OVERRIDES
    # --------------------------------------------------

    def _check_can_validate(self):
        if any(cost.state != "approved" for cost in self):
            raise UserError(_("Only approved landed costs can be validated"))

        for cost in self:
            if not cost._get_targeted_move_ids():
                raise UserError(_("No stock moves found for landed cost"))

    def _check_sum(self):
        """ Check if each cost line its valuation lines sum to the correct amount
        and if the overall total amount is correct also """
        prec_digits = self.env.company.currency_id.decimal_places
        dutyLines = self.cost_lines.filtered(lambda l: l.product_id.is_duty == True)
        percentLines = self.cost_lines.filtered(lambda l: l.split_method == "by_percentage")
        for landed_cost in self:
            total_amount = sum(landed_cost.valuation_adjustment_lines.mapped('additional_landed_cost'))
            if not tools.float_is_zero(total_amount - landed_cost.amount_total,
                                       precision_digits=prec_digits) and not dutyLines and not percentLines:
                return False

            val_to_cost_lines = defaultdict(lambda: 0.0)
            for val_line in landed_cost.valuation_adjustment_lines:
                val_to_cost_lines[val_line.cost_line_id] += val_line.additional_landed_cost
            if any(not tools.float_is_zero(cost_line.price_unit - val_amount, precision_digits=prec_digits)
                   for cost_line, val_amount in val_to_cost_lines.items()) and not dutyLines and not percentLines:
                return False
        return True

    def button_validate(self):
        res = super().button_validate()
        self.post_date = fields.Date.today()
        self.final_landed_cost()
        return res

    # --------------------------------------------------
    # FINAL COST UPDATE
    # --------------------------------------------------

    # def final_landed_cost(self):
    #     product_summary = defaultdict(lambda: {
    #         "qty": 0.0,
    #         "purchase_casting_us": 0.0,
    #         "insurance_cost": 0.0,
    #         "total_landed_cost": 0.0,
    #     })
    #
    #     for line in self.valuation_adjustment_lines:
    #         product_summary[line.product_id.id]["qty"] += line.quantity
    #         product_summary[line.product_id.id]["purchase_casting_us"] += line.purchase_casting_us
    #         product_summary[line.product_id.id]["total_landed_cost"] += line.additional_landed_cost
    #         if line.cost_line_id.split_method == "by_percentage":
    #             product_summary[line.product_id.id]["insurance_cost"] += line.additional_landed_cost
    #
    #     for product_id, vals in product_summary.items():
    #         total_cost = (
    #             vals["purchase_casting_us"]
    #             + vals["total_landed_cost"]
    #             - vals["insurance_cost"]
    #         )
    #         unit_cost = total_cost / vals["qty"] if vals["qty"] else 0.0
    #
    #         product = self.env["product.product"].sudo().browse(product_id)
    #         product.write({
    #             "prev_landed_cost": product.landed_cost,
    #             "landed_cost": unit_cost,
    #         })
    def final_landed_cost(self):
        product_summary_dict = {}

        for line in self.valuation_adjustment_lines:
            # Calculate insurance cost if method is by_percentage
            insurance_cost = line.additional_landed_cost if line.cost_line_id.split_method == 'by_percentage' else 0.0

            # Aggregate data per product
            if line.product_id.id not in product_summary_dict:
                product_summary_dict[line.product_id.id] = {
                    "qty": line.quantity,
                    "purchase_cost": line.purchase_cost,
                    "purchase_casting_us": line.purchase_casting_us,
                    "total_cost_with_insurance": line.additional_landed_cost or 0.0,
                    "insurance_cost": insurance_cost or 0.0,
                    "duty_rate": line.casting_rate,
                }
            else:
                product_data = product_summary_dict[line.product_id.id]
                product_data["qty"] += line.quantity
                product_data["total_cost_with_insurance"] += line.additional_landed_cost
                product_data["insurance_cost"] += insurance_cost
                product_data["duty_rate"] += line.casting_rate
                # purchase_cost and purchase_casting_us remain unchanged (assume first line as base)

        # Compute final unit landed cost per product
        for product_id, summary in product_summary_dict.items():
            total_cost = 0.0
            total_cost_with_insurance = 0.0

            if summary.get('total_cost_with_insurance') and summary.get('purchase_casting_us'):
                total_cost = (summary['total_cost_with_insurance'] + summary['purchase_casting_us']) - summary[
                    'insurance_cost']

            if summary.get('insurance_cost', 0.0) > 0.0 and summary.get('purchase_casting_us') and summary.get(
                    'total_cost_with_insurance'):
                total_cost_with_insurance = summary['purchase_casting_us'] + summary['total_cost_with_insurance']

            # Determine unit cost
            if total_cost_with_insurance > 0.0 and summary.get('qty'):
                unit_cost = total_cost_with_insurance / summary['qty']
            else:
                unit_cost = total_cost / summary.get('qty', 1)  # prevent division by zero

            # Update product record
            product = self.env['product.product'].sudo().browse(product_id)
            product.write({
                'prev_landed_cost': product.landed_cost,
                'landed_cost': unit_cost,
            })


# --------------------------------------------------
# LANDED COST LINE
# --------------------------------------------------

class LandedCostLine(models.Model):
    _inherit = "stock.landed.cost.lines"

    price_unit = fields.Float(string="Cost in Company Currency")
    duty_rate = fields.Float(string="Rate of Duty")

    currency_id = fields.Many2one(
        related="cost_id.currency_id",
        store=True,
    )

    currency_price_unit = fields.Monetary(
        string="Cost",
        currency_field="currency_id",
    )

    split_method = fields.Selection(
        selection=SPLIT_METHOD,
        required=True,
    )

    # usd_amount = fields.Monetary(
    #     string="Amount (USD)",
    #     currency_field='usd_currency_id'
    # )
    #
    # usd_currency_id = fields.Many2one(
    #     'res.currency',
    #     default=lambda self: self.env.ref('base.USD'),
    #     readonly=False
    # )

    # @api.onchange('usd_amount', 'cost_id.currency_exchange_rate')
    # def _onchange_usd_amount(self):
    #     company_currency = self.env.company.currency_id  # MUR
    #     usd = self.env.ref('base.USD')
    #     for line in self:
    #         if line.usd_amount:
    #             line.currency_price_unit = line.usd_amount * line.cost_id.currency_exchange_rate

    @api.onchange("currency_price_unit", "cost_id.currency_exchange_rate")
    def _onchange_currency_price_unit(self):
        for rec in self:
            if rec.cost_id.currency_id != rec.cost_id.company_id.currency_id:
                rec.price_unit = rec.currency_price_unit * rec.cost_id.currency_exchange_rate
            else:
                rec.price_unit = rec.currency_price_unit

    @api.onchange("product_id")
    def onchange_product_id(self):
        res = super().onchange_product_id()
        self.currency_price_unit = self.price_unit
        return res


# --------------------------------------------------
# VALUATION ADJUSTMENT LINES
# --------------------------------------------------

class AdjustmentLines(models.Model):
    _inherit = "stock.valuation.adjustment.lines"

    unit_cost = fields.Float(string="Unit Cost US", digits="Product Price", readonly=True)
    purchase_cost = fields.Float(string="Purchase Cost", digits="Product Price")
    purchase_currency_id = fields.Many2one("res.currency")
    landed_cost_per_unit = fields.Monetary(string="Unit Cost")
    casting_rate = fields.Float(string="Rate of Duty", digits="Product Price")
    casting_rate_amount = fields.Float(string="Duty Amount", digits="Product Price")
    purchase_casting_us = fields.Monetary(string="Total Cost")
    purchase_line_id = fields.Many2one("purchase.order.line", readonly=True)
    quantity = fields.Float(
        string="Quantity",
        default=1.0,
        required=True,
        digits="Product Unit of Measure",
    )

    # def write(self, vals):
    #     res = super().write(vals)
    #
    #     if "additional_landed_cost" in vals:
    #         for line in self:
    #             cost_val_line = self.env["cost.valuation.lines"].search([
    #                 ("cost_id", "=", line.cost_id.id),
    #                 ("product_id", "=", line.product_id.id),
    #             ], limit=1)
    #
    #             if cost_val_line:
    #                 # Identify which charge this is based on cost line product
    #                 name = line.cost_line_id.product_id.name.lower()
    #
    #                 if "duty" in name:
    #                     cost_val_line.duty_charge_amount = line.additional_landed_cost
    #                 elif "freight" in name:
    #                     cost_val_line.freight_charge_amount = line.additional_landed_cost
    #                 elif "local" in name:
    #                     cost_val_line.local_charge_amount = line.additional_landed_cost
    #                 elif "fumigation" in name:
    #                     cost_val_line.fumigation_charge_amount = line.additional_landed_cost
    #                 elif "others" in name:
    #                     cost_val_line.others_charge_amount = line.additional_landed_cost
    #                 elif "insurance" in name:
    #                     cost_val_line.insurance_charge_amount = line.additional_landed_cost
    #
    #     return res
