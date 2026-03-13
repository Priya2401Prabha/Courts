# -*- coding: utf-8 -*-
from odoo import models


class StockLandedCostXlsx(models.AbstractModel):
    _name = 'report.stock_landed_cost_excel_report.landed_cost_xlsx'
    _description = 'Stock Landed Cost Excel Report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, records):
        for obj in records:
            company_format = workbook.add_format({
                'bg_color': 'black', 'align': 'center', 'font_size': 25, 'font_color': 'white'
            })
            order_format = workbook.add_format({
                'bg_color': 'black', 'align': 'center', 'font_size': 14, 'font_color': 'white', 'border': 1
            })
            table_header_center = workbook.add_format({
                'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
                'bg_color': 'black', 'font_size': 12, 'font_color': 'white'
            })
            table_header_left = workbook.add_format({
                'bg_color': 'black', 'align': 'left', 'font_size': 12, 'font_color': 'white', 'text_wrap': True
            })
            table_row_left = workbook.add_format({'align': 'left', 'font_size': 12, 'border': 1})
            table_row_right = workbook.add_format({'align': 'right', 'font_size': 12, 'border': 1})
            table_row_center = workbook.add_format({'align': 'center', 'font_size': 12, 'border': 1})

            # Create worksheet
            worksheet = workbook.add_worksheet(obj.name or "Landed Cost")
            worksheet.merge_range('A2:F3', obj.company_id.name, company_format)
            worksheet.merge_range('A5:F5', f'Landed Costs :- {obj.name}', order_format)

            # Header example
            worksheet.merge_range('B7:C7', 'Date', table_header_center)
            worksheet.merge_range('D7:F7', str(obj.date), table_row_center)
            worksheet.write(10, 8, "Currency Exchange Rate", table_header_center)
            worksheet.write(12, 8, obj.currency_exchange_rate or 1.0, table_row_right)

            # Example of column headers
            row = 14
            worksheet.write(row, 0, 'P. Code', table_header_center)
            worksheet.write(row, 1, 'Description', table_header_center)
            worksheet.write(row, 2, 'UOM', table_header_center)
            worksheet.write(row, 3, 'STK', table_header_center)
            worksheet.write(row, 4, 'Unit Volume', table_header_center)
            worksheet.write(row, 5, 'Total Volume', table_header_center)
            worksheet.write(row, 6, 'Unit Cost Per Product', table_header_center)
            worksheet.write(row, 7, 'Total Cost Us', table_header_center)
            worksheet.write(row, 8, 'Total Cost In Rs', table_header_center)

            # Fill in rows
            row += 1
            for line in obj.valuation_adjustment_lines:
                worksheet.write(row, 0, line.product_id.default_code or '', table_row_center)
                worksheet.write(row, 1, line.product_id.display_name or '', table_row_left)
                worksheet.write(row, 2, line.product_id.uom_id.name or '', table_row_left)
                worksheet.write(row, 3, line.quantity, table_row_right)
                worksheet.write(row, 4, line.unit_volume, table_row_right)
                worksheet.write(row, 5, line.volume, table_row_right)
                worksheet.write(row, 6, line.purchase_cost or 0.0, table_row_right)
                worksheet.write(row, 7, line.purchase_casting_us or 0.0, table_row_right)
                worksheet.write(row, 8, line.purchase_casting_rs or 0.0, table_row_right)
                row += 1
