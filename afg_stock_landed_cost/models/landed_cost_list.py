# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import sys
import logging

_logger = logging.getLogger(__name__)
_logger.info("ODOO PYTHON EXECUTABLE: %s", sys.executable)


class CostValuationLine(models.Model):
    _name = "cost.valuation.lines"
    _description = "Freight Charge Line"
    _rec_name = "product_id"

    name = fields.Char(
        string="Description",
        compute="_compute_name",
        store=True,
    )

    cost_id = fields.Many2one(
        "stock.landed.cost",
        string="Landed Cost",
        required=True,
        ondelete="cascade",
    )

    cost_line_id = fields.Many2one(
        "stock.landed.cost.lines",
        string="Cost Line",
        readonly=True,
    )

    move_id = fields.Many2one(
        "stock.move",
        string="Stock Move",
        readonly=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        domain="[('landed_cost_ok', '=', True)]",
        readonly=True,
    )

    p_code = fields.Char(
        related="product_id.default_code",
        string="Code",
        readonly=True,
        store=True,
    )

    uom_id = fields.Many2one(
        related="product_id.uom_id",
        string="UOM",
        readonly=True,
        store=True,
    )

    quantity = fields.Float(
        string="Quantity",
        default=1.0,
        required=True,
        digits="Product Unit of Measure",
    )

    weight = fields.Float(
        string="Weight",
        default=1.0,
        digits="Stock Weight",
    )

    volume = fields.Float(
        string="Total Volume",
        default=1.0,
        digits="Volume",
    )

    unit_volume = fields.Float(
        string="Unit Volume",
        compute="_compute_unit_volume",
        store=True,
        digits="Volume",
    )

    former_cost = fields.Monetary(string="Original Value")
    additional_landed_cost = fields.Monetary(string="Additional Landed Cost")

    currency_id = fields.Many2one(
        related="cost_id.company_id.currency_id",
        store=True,
    )

    company_currency_id = fields.Many2one(
        related="cost_id.company_id.currency_id",
        store=True,
    )

    unit_cost = fields.Float(
        string="Unit Cost Rs",
        readonly=True,
        digits="Product Price",
    )

    purchase_cost = fields.Float(
        string="Unit Cost $",
        digits="Product Price",
        help="Purchase Unit Cost",
    )

    purchase_currency_id = fields.Many2one("res.currency")

    landed_cost_per_unit = fields.Float(
        string="Unit Landed Cost Rs",
        compute="_compute_total_amount",
        store=True,
        digits="Product Price",
    )

    landed_cost_per_unit_us = fields.Float(
        string="Unit Landed Cost $",
        compute="_compute_landed_unit_factor",
        store=True,
        digits="Product Price",
    )

    factor_us_unit_cost = fields.Float(
        string="Factor",
        compute="_compute_landed_unit_factor",
        store=True,
        digits="Product Price",
    )

    purchase_casting_us = fields.Float(
        string="Total Cost ($)",
        compute="_compute_purchase_cost_us",
        store=True,
        digits="Product Price",
    )

    purchase_casting_rs = fields.Float(
        string="Total Cost (Rs)",
        compute="_compute_purchase_cost_us",
        store=True,
        digits="Product Price",
    )

    purchase_line_id = fields.Many2one(
        "purchase.order.line",
        string="Purchase Order Line",
        readonly=True,
    )

    freight_charge_amount = fields.Float(string="Freight Charge", digits="Local Charge")
    local_charge_amount = fields.Float(string="Local Charge", digits="Local Charge")
    duty_rate = fields.Float(string="Duty Rate (%)", digits="Local Charge")
    duty_charge_amount = fields.Float(string="Duty Amount", digits="Local Charge")
    fumigation_charge_amount = fields.Float(string="Fumigation", digits="Local Charge")
    others_charge_amount = fields.Float(string="Others Charge", digits="Local Charge")
    insurance_charge_amount = fields.Float(string="Insurance Amount", digits="Local Charge")

    total_cost = fields.Float(
        string="Total Cost",
        compute="_compute_total_amount",
        store=True,
        digits="Local Charge",
    )

    total_cost_with_insurance = fields.Float(
        string="Total Cost with Insurance",
        compute="_compute_total_amount",
        store=True,
        digits="Local Charge",
    )

    @api.onchange("duty_charge_amount")
    def onchange_additional_landed_cost(self):
        for rec in self:
            valuation_id = self.env['stock.valuation.adjustment.lines'].search(
                [('product_id', '=', rec.product_id.id), ('cost_id', '=', rec._origin.cost_id.id),
                 ('name', 'ilike', 'Duty')])
            if rec.duty_charge_amount:
                valuation_id.write({'additional_landed_cost': rec.duty_charge_amount})

    def write(self, vals):
        res = super().write(vals)
        if 'duty_charge_amount' in vals:
            self.onchange_additional_landed_cost()
        return res

    # ---------------- COMPUTES ---------------- #

    @api.depends("product_id")
    def _compute_name(self):
        for line in self:
            line.name = line.product_id.display_name or ""

    @api.depends("volume", "quantity")
    def _compute_unit_volume(self):
        for line in self:
            line.unit_volume = line.volume / line.quantity if line.quantity else 0.0

    @api.depends("purchase_cost", "quantity", "fumigation_charge_amount", "purchase_line_id.price_subtotal",
                 "cost_id.currency_exchange_rate",
                 )
    def _compute_purchase_cost_us(self):
        for line in self:
            # if not line.fumigation_charge_amount:
            line.purchase_casting_us = line.purchase_cost * line.quantity
            # else:
            #     line.purchase_casting_us = line.purchase_cost * line.quantity + line.fumigation_charge_amount

            if line.purchase_line_id and line.cost_id.currency_exchange_rate:
                line.purchase_casting_rs = (
                        line.purchase_line_id.price_subtotal
                        * line.cost_id.currency_exchange_rate
                        + line.fumigation_charge_amount
                )
            else:
                line.purchase_casting_rs = 0.0

    @api.depends("purchase_casting_rs", "fumigation_charge_amount", "purchase_line_id.price_subtotal",
                 "freight_charge_amount", "local_charge_amount", "insurance_charge_amount", "duty_charge_amount",
                 "others_charge_amount", "quantity", "landed_cost_per_unit_us", "cost_id.currency_exchange_rate",
                 "unit_cost", "landed_cost_per_unit", )
    def _compute_total_amount(self):
        for line in self:
            base_cost = (
                    line.purchase_casting_rs
                    + line.freight_charge_amount
                    + line.local_charge_amount
                    + line.duty_charge_amount
                    + line.others_charge_amount
                    + line.fumigation_charge_amount
            )
            line.total_cost = base_cost
            line.total_cost_with_insurance = base_cost + line.insurance_charge_amount
            line.landed_cost_per_unit = (
                line.total_cost_with_insurance / line.quantity
                if line.quantity
                else 0.0
            )

    @api.depends("purchase_cost", "landed_cost_per_unit", "cost_id.currency_exchange_rate")
    def _compute_landed_unit_factor(self):
        for line in self:
            line.landed_cost_per_unit_us = (
                line.landed_cost_per_unit / line.cost_id.currency_exchange_rate
                if line.cost_id.currency_exchange_rate else 0.0
            )

            if line.landed_cost_per_unit_us and line.purchase_cost:
                line.factor_us_unit_cost = line.landed_cost_per_unit_us / line.purchase_cost
            else:
                line.factor_us_unit_cost = 0.0

    @api.depends("total_cost",'cost_id.insurance_amount')
    def compute_insurance_new(self):
        for cost in self.mapped('cost_id'):

            lines = self.filtered(lambda l: l.cost_id == cost)
            total_insurance = 0.0

            for line in lines:
                # 1️⃣ Calculate insurance per product
                insurance_amount = (
                        line.total_cost * cost.insurance_amount / 100
                )

                line.insurance_charge_amount = insurance_amount
                total_insurance += insurance_amount

                # 2️⃣ Update valuation adjustment line
                valuation_line = self.env['stock.valuation.adjustment.lines'].search([
                    ('product_id', '=', line.product_id.id),
                    ('cost_id', '=', cost.id),
                    ('name', 'ilike', 'Insurance')
                ], limit=1)

                if valuation_line:
                    valuation_line.additional_landed_cost = insurance_amount

            # 3️⃣ Update Insurance Landed Cost Line (TOTAL)
            insurance_cost_line = cost.cost_lines.filtered(
                lambda l: l.split_method == 'by_percentage'
                          and 'insurance' in l.name.lower()
            )

            if insurance_cost_line:
                insurance_cost_line.write({
                    'price_unit': total_insurance,
                    'currency_price_unit': total_insurance,
                })
        # for line in self:
        #     line.insurance_charge_amount = line.total_cost * line.cost_id.insurance_amount / 100
        #
        #     if line.inusrance_charge_amount:
        #         valuation_id = self.env['stock.valuation.adjustment.lines'].search(
        #             [('product_id', '=', rec.product_id.id), ('cost_id', '=', rec._origin.cost_id.id),
        #              ('name', 'ilike', 'Insurance')])
        #         valuation_id.write({'additional_landed_cost': rec.inusrance_charge_amount})
        #
        #     cost_line = self.env['stock.landed.cost.lines'].search([('name','ilike', 'Insurance'), ('split_method', '=', 'by_percentage')])
        #     cost_line.write({'price_unit': total_inusrance_charge_amount, 'currency_price_unit': total_insurance_charge_amount})



