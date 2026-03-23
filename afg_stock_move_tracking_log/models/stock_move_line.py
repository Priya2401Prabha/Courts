from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class StockMoveLine(models.Model):
    # _name = 'afg.product.template'
    _inherit = "stock.move.line"
    _description = "Stock Move Line"

    valuation_value = fields.Float(
        string="Valuation",
        compute='_compute_valuation_value',
        store=True
    )

    is_usage_location = fields.Boolean(
        string='Usage Location',
        related='location_id.is_usage_location',
        store=True
    )

    @api.depends('product_id', 'picking_id')
    def _compute_valuation_value(self):
        for line in self:
            value = 0.0

            if line.product_id and line.picking_id:
                valuation_layers = self.env['stock.valuation.layer'].search([
                    ('product_id', '=', line.product_id.id),
                    ('stock_move_id.picking_id', '=', line.picking_id.id),
                ])

                # Sum all valuation values
                value = sum(valuation_layers.mapped('value'))

            line.valuation_value = value


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def create(self, vals_list):
        records = super().create(vals_list)

        for rec in records:
            if rec.stock_move_id and rec.stock_move_id.picking_id:
                move_lines = rec.stock_move_id.move_line_ids
                move_lines._compute_valuation_value()

        return records

    def write(self, vals):
        res = super().write(vals)

        for rec in self:
            if rec.stock_move_id and rec.stock_move_id.picking_id:
                move_lines = rec.stock_move_id.move_line_ids
                move_lines._compute_valuation_value()

        return res