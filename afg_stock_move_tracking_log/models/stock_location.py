from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup
class StockLocation(models.Model):
    _inherit = "stock.location"

    is_usage_location = fields.Boolean(string='Usage Location')