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

from odoo import _,models, fields, api
from odoo.exceptions import UserError, ValidationError

class StockForecastResult(models.TransientModel):
	_name = 'stock.forecast.result'
	_description = 'Stock Forecast Result'


	wizard_id = fields.Many2one(
			"stock.forecast.wizard",
			string="Wizard",
			help="Reference to the stock forecast wizard used for this result."
		)
	product_id = fields.Many2one(
		"product.product",
		string="Product",
		help="Product for which the forecast result is generated."
	)
	average_daily = fields.Float(
		string="Avg. Daily Consumption",
		help="Average daily consumption of the product "
			 "based on historical data."
	)
	forecasted_demand = fields.Float(
		string="Forecasted Demand",
		help="Predicted demand for the product within the selected horizon."
	)
	current_available_qty = fields.Float(
		string="Cur. Net Qty",
		help="Current available stock quantity of the product."
	)
	required_qty = fields.Float(
		string="Req. Qty To Procure/Produce",
		help="Quantity that needs to be procured or produced "
			 "to meet the forecasted demand."
	)
	sold_qty = fields.Float(
		string="Sold Qty",
		help="Total sold quantity of the product within the selected period."
	)
	mrp_consumed_qty = fields.Float(
		string="MRP Consumed Qty",
		help="Quantity of the product consumed in Manufacturing Orders "
			 "within the selected period."
	)
	can_serve_days = fields.Float(
		string="Can Serve Days",
		help="Number of days the current stock can serve based on "
			 "average daily consumption."
	)


	def action_create_rfq(self):
		"""
		   Create a Purchase Order (RFQ) for the required quantity 
		   of products from the forecast result.

		   Steps performed:
		   1. Iterate over forecast result records.
		   2. Skip products that do not require additional procurement 
			  (required_qty <= 0).
		   3. Identify the vendor from the product's vendor list 
			  (`seller_ids`), picking the first available vendor.
		   4. If no vendor is found, raise a ValidationError.
		   5. Create a purchase order with:
			  - Selected vendor
			  - Product details (name, UoM, quantity, price)
		   6. If only one record is processed, open the created Purchase 
			  Order in form view for quick review.

		   :return: dict (action to open the created purchase order in form view, 
						  if only one PO is created).
	   """
		PurchaseOrder = self.env['purchase.order']
		for rec in self:
			if rec.required_qty <= 0:
				continue
			vendor = rec.product_id.seller_ids and rec.product_id.seller_ids[0].partner_id or False
			
			if not vendor:
				raise ValidationError(_('No vendor found for product %s' % rec.product_id.display_name))

			po = PurchaseOrder.create({
			'partner_id': vendor.id,
			'order_line': [(0, 0, {
			'product_id': rec.product_id.id,
			'name': rec.product_id.display_name,
			'product_qty': rec.required_qty or 1,
			'product_uom': rec.product_id.uom_id.id,
			'price_unit': rec.product_id.standard_price or 0.0,
			})]
			})
			# Open PO form
			if len(self) == 1:
				return {
				'type': 'ir.actions.act_window',
				'res_model': 'purchase.order',
				'view_mode': 'form',
				'res_id': po.id,
				'target': 'current',
				}
			
			

	def action_create_mo(self):
		"""
			Create Manufacturing Orders (MO) for the selected product(s) based on the required quantity.

			- Skips records where `required_qty` is less than or equal to zero.
			- Uses the first available Bill of Materials (BOM) if present for the product.
			- Creates a new `mrp.production` record with the product, quantity, UoM, and BOM.
			- If only one record is processed, it returns an action to directly open the created MO in form view.

			Returns:
				dict: An action to open the created Manufacturing Order if a single record is processed,
					  otherwise None.
		"""
		Production = self.env['mrp.production']
		for rec in self:
			if rec.required_qty <= 0:
				continue
			# if not rec.product_id.bom_ids:
			# 	raise ValidationError(_('No BOM found for product %s' % rec.product_id.display_name))
			
			mo = Production.create({
			'product_id': rec.product_id.id,
			'product_qty': rec.required_qty or 1,
			'product_uom_id': rec.product_id.uom_id.id,
			'bom_id': rec.product_id.bom_ids[0].id if rec.product_id.bom_ids else False,
			})
			if len(self) == 1:
				return {
				'type': 'ir.actions.act_window',
				'res_model': 'mrp.production',
				'view_mode': 'form',
				'res_id': mo.id,
				'target': 'current',
				}
			
