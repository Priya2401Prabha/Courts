{
    'name': 'stock_move_tracking_log',
    'version': '1.0',
    'summary': '',
    'sequence': 10,
    'author': 'Priya',
    'website': '',
    'description': """
        It will track the fields of Transfers in the log 
    """,
    'category': 'Tools',
    'depends': ['stock', 'sale_management', 'product', 'report_xlsx'],
    'data': [
         'views/product_report_view_afg.xml',
         'reports/report.xml',

    ],
    'demo': [
    ],
    'price': 0.0,
    'currency': 'EUR',
    'support': 'Shanmugapriya@rhodes.mu',
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
