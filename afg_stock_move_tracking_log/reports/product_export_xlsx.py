from odoo import models


from odoo import models
from datetime import datetime, timedelta

class ProductExportXlsx(models.AbstractModel):
    _name = 'report.afg_stock_move_tracking_log.product_export_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, products):

        sheet = workbook.add_worksheet('Products')

        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center'
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center'
        })

        date_format = workbook.add_format({
            'align': 'center'
        })

        # Current date info
        today = datetime.today()
        # week = today.strftime("%U")
        # year = today.year
        # date_str = today.strftime("%d-%m-%Y")
        column_widths = [15, 25, 20, 20, 20, 15, 20, 18, 18, 15, 18, 15, 15, 25]
        for col, width in enumerate(column_widths):
            sheet.set_column(col, col, width)
        # Report Details

        # Report Title (merge across columns)
        sheet.merge_range('A1:M1', 'Product Report', title_format)

        from_dates = [p.from_date for p in products if p.from_date]
        start_date  = min(from_dates)
        to_date = start_date + timedelta(days=7)
        # to_dates = [p.to_date for p in products if p.to_date]

        if from_dates and to_date:
            overall_from = min(from_dates).strftime("%d-%m-%Y")
            overall_to = to_date.strftime("%d-%m-%Y")
            week_number = min(from_dates).strftime("%U")  # Taking week of first from_date
            sheet.merge_range('A2:M2', f'From {overall_from} - To {overall_to} / Week {week_number}', date_format)
        else:
            sheet.merge_range('A2:M2', '', date_format)

        headers = [
            'Product code', 'Description', 'Vendor', 'Brand Name', 'Product Category',
            'Quantity On Hand', 'On Hand Total Value', 'Weekly Sold Units',
            'Weekly Sold Value', 'YTD Units', 'YTD Values',
            'Cost/Avg Price', 'Retail Price'
        ]

        # Header Row
        for col, header in enumerate(headers):
            sheet.write(3, col, header, header_format)

        row = 4

        for product in products:
            sheet.write(row, 0, product.default_code or '')
            sheet.write(row, 1, product.name)
            sheet.write(row, 2, product.default_vendor_id.name if product.default_vendor_id else '')
            sheet.write(row, 3, product.brand_name or '')
            sheet.write(row, 4, product.categ_id.name if product.categ_id else '')
            sheet.write(row, 5, product.qty_available)
            sheet.write(row, 6, product.onhand_valuation_value)
            sheet.write(row, 7, product.weekly_sold_units)
            sheet.write(row, 8, product.weekly_sold_value)
            sheet.write(row, 9, product.year_sold_units)
            sheet.write(row, 10, product.year_sold_value)
            sheet.write(row, 11, product.standard_price)
            sheet.write(row, 12, product.list_price)

            row += 1
