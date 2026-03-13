# -*- coding: utf-8 -*-
###############################################################################
#
#    Datahat Solutions LLP
#
#    Copyright (C) 2023-TODAY Datahat Solutions LLP (<https://www.datahatsolutions.com>)
#    Author: Datahat Solutions LLP (info@datahatcs.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import _,api,fields,models
from datetime import timedelta
from odoo.tools.misc import format_date
from odoo.exceptions import UserError, ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta

class StockForecastWizard(models.TransientModel):
	_name = 'stock.forecast.wizard'
	_description = 'Stock Forecast Wizard'


	product_ids = fields.Many2many(
		"product.product",
		string="Products",
		help="Select specific products to include in the forecast. "
			 "Leave empty to use the product category instead."
	)
	category_id = fields.Many2one(
		"product.category",
		string="Product Category",
		help="Choose a product category to include all products "
			 "within that category in the forecast."
	)
	date_from = fields.Date(
		string="From",
		help="Start date for the forecast period."
	)
	date_to = fields.Date(
		string="To",
		help="End date for the forecast period."
	)
	horizon_days = fields.Integer(
		string="Horizon (days)",
		default=30,
		help="Number of days to forecast ahead from the selected period."
	)
	horizon_unit = fields.Selection(
		[
			("day", "Days"),
			("week", "Weeks"),
			("month", "Months"),
		],
		string="Horizon Unit",
		default="day",
		help="Unit of time (days, weeks, or months) to apply to "
			 "the forecast horizon."
	)
	type_of_consumption = fields.Selection(
		[
			("sales", "Sales Deliveries"),
			("production", "Manufacturing Consumption"),
			("both", "Both"),
		],
		string="Type of Consumption",
		default="both",
		help="Choose whether to calculate forecast based on sales "
			 "deliveries, manufacturing consumption, or both."
	)

	buffer_stock = fields.Float(
			string="Buffer Stock (%)",
			help="Increase required stock by this percentage."
		)

	date_range_type = fields.Selection([
			('last_3', 'Last 3 Months'),
			('last_6', 'Last 6 Months'),
			('last_12', 'Last 12 Months'),
			('custom', 'Custom'),
		], 
		string="Date Range", 
		default="custom",
		help="Select a predefined date range (last 3, 6, or 12 months) "
              "or choose 'Custom' to manually define your own start and end dates."
	)

	forecast_method = fields.Selection([
		('reorder_rule', 'Reorder Rule'),
		('history_base', 'History Based'),
	], 
	string="Forecast Method", 
	default="history_base", 
	required=True,
	help="Choose how the forecast should be calculated:\n"
	     "- Reorder Rule: Uses product reorder rules (Min/Max quantities).\n"
	     "- History Based: Uses past sales and manufacturing consumption to predict demand."
	)


	@api.onchange('date_range_type')
	def _onchange_date_range_type(self):
		today = date.today()
		if self.date_range_type == 'last_3':
			self.date_to = today
			self.date_from = today - relativedelta(months=3)
		elif self.date_range_type == 'last_6':
			self.date_to = today
			self.date_from = today - relativedelta(months=6)
		elif self.date_range_type == 'last_12':
			self.date_to = today
			self.date_from = today - relativedelta(months=12)
		elif self.date_range_type == 'custom':
			self.date_from = False
			self.date_to = False

	@api.constrains('date_from', 'date_to')
	def _check_date_range(self):
		"""
		Constraint method to validate the date range.

		Ensures that the 'From' date is not greater than the 'To' date.
		If the condition is violated, a ValidationError will be raised.
		"""
		for rec in self:
			if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
				raise ValidationError(_("Start Date cannot be greater than End Date."))

	
	def _horizon_days(self):
		"""
			Compute the forecast horizon in days based on the selected
			horizon value and unit.

			- If the unit is 'day', returns the value as is.
			- If the unit is 'week', multiplies the value by 7.
			- If the unit is 'month', approximates each month as 30 days.
			- Defaults to 0 if no value is set.

			:return: int, forecast horizon expressed in days.
		"""
		self.ensure_one()
		val = self.horizon_days or 0
		if self.horizon_unit == "day":
			return val
		if self.horizon_unit == "week":
			return val * 7
		if self.horizon_unit == "month":
			# Approximate as 30 days per month
			return val * 30
		return val

	def _get_sales_consumption(self, product):
		"""
			Calculate the delivered quantity of a given product 
			from confirmed sales within the selected date range.

			- Filters stock moves where:
				* State = 'done'
				* Date is between 'date_from' and 'date_to'
				* Linked to a sales order line (sale_line_id != False)
				* Matches the given product
			- Sums up the delivered quantity (`quantity`) 
			  from the matching stock moves.

			:param product: record of product.product for which sales 
							consumption is to be calculated.
			:return: float, total delivered (consumed) sales quantity.
		"""
		domain = [
			('state', '=', 'done'),
			('date', '>=', self.date_from),
			('date', '<=', self.date_to),
			('sale_line_id', '!=', False),
			('product_id', '=', product.id),
		]
		moves = self.env['stock.move'].search(domain)
		return sum(m.quantity for m in moves)

	def _get_mrp_consumption(self, product):
		"""
			Calculate the consumed quantity of a given product 
			as a component in Manufacturing Orders (MO) 
			within the selected date range.

			- Filters stock moves where:
				* State = 'done'
				* Date is between 'date_from' and 'date_to'
				* Linked to a Manufacturing Order (raw_material_production_id != False)
				* Matches the given product
			- Sums up the consumed quantity (`quantity`) 
			  from the matching stock moves.

			:param product: record of product.product for which 
							manufacturing consumption is to be calculated.
			:return: float, total consumed quantity in MOs.
		"""
		domain = [
			('state', '=', 'done'),
			('date', '>=', self.date_from),
			('date', '<=', self.date_to),
			('raw_material_production_id', '!=', False),
			('product_id', '=', product.id),
		]
		moves = self.env['stock.move'].search(domain)
		return sum(m.quantity for m in moves)

	def action_confirm(self):
		"""
			This method generates the stock forecast report based on the selected forecast method 
			(history-based consumption or reorder rules). It calculates average consumption, 
			forecasted demand, available stock, required quantity, and service days for each product, 
			then creates forecast result records and returns an action to display them in a list view.
		"""
		# compute products list
		products = self.product_ids
		if not products and self.category_id:
			products = self.env['product.product'].search([('categ_id', 'child_of', self.category_id.id)])
		if self.forecast_method =='history_base':
			if self.date_from and  self.date_to:
				days = (fields.Date.from_string(self.date_to) - fields.Date.from_string(self.date_from)).days + 1
			if days <= 0:
				days = 1
		else:
			days = 1


		horizon_days = max(self._horizon_days(), 0)
		results = []
		for product in products:
			avg_daily = 0.0
			forecasted = 0.0
			required_qty = 0.0
			sold_qty = 0.0 
			mrp_consumed_qty = 0.0
			if self.forecast_method =='history_base':
				if self.type_of_consumption =='sales' or self.type_of_consumption =='both':
					sold_qty = self._get_sales_consumption(product)
				if self.type_of_consumption =='production' or self.type_of_consumption =='both':
					mrp_consumed_qty = self._get_mrp_consumption(product)
				consumed = sold_qty+ mrp_consumed_qty
				avg_daily = consumed / days
				forecasted = avg_daily * horizon_days
				required_qty = max(0.0, round(forecasted - product.virtual_available, 2))
				if self.buffer_stock:
					required_qty *=  (1 + (self.buffer_stock) / 100.0)

			if self.forecast_method == 'reorder_rule':
				orderpoint = self.env['stock.warehouse.orderpoint'].search(
					[('product_id', '=', product.id)], limit=1)
				if orderpoint and orderpoint.product_max_qty:
					forecasted = orderpoint.product_max_qty
					if product.virtual_available < forecasted:
						required_qty = forecasted - product.virtual_available

			res = self.env['stock.forecast.result'].create({
			'product_id': product.id,
			'average_daily':avg_daily,
			'forecasted_demand': forecasted,	
			'current_available_qty': product.virtual_available,
			'required_qty': required_qty,
			'sold_qty':sold_qty,
			'mrp_consumed_qty':mrp_consumed_qty,
			'can_serve_days': max(0,round(product.virtual_available/avg_daily,2) if avg_daily else 0),
			'wizard_id': self.id,
			})
			results.append(res.id)
		if self.forecast_method == 'reorder_rule':
			tree_view_id = self.env.ref('dh_forecast_report.view_stock_forecast_result_based_on_reorder_rules_tree').id
		if self.forecast_method == 'history_base':
			tree_view_id = self.env.ref('dh_forecast_report.view_stock_forecast_result_based_on_history_tree').id
		action = {
			'type': 'ir.actions.act_window',
			'views': [(tree_view_id, 'list')],
			'view_mode': 'list',
			'name': _('Forecast Report'),
			'res_model': 'stock.forecast.result',
			'context':{"create":False,'edit':False},
			'domain': [('wizard_id','=',self.id)],
			'display_name': f'''Forecast Report {format_date(self.env, self.date_from)} To {format_date(self.env, self.date_to)}''',
		}
		return action

