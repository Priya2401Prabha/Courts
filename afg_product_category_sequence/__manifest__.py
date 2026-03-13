{
    'name': 'Product Automatic/manual Internal Reference',
    'version': '1.0',
    'summary': '',
    'sequence': 10,
    'author': 'Priya',
    'website': '',
    'images': ['static/description/product_categories_arborescence.png'],
    'description': """
        Category-wise product sequence:
        - Automatic and manual sequence generation
        - Child category inherits parent rules
        - Multi-company support
        - Track manual overrides
    """,
    'category': 'Inventory/Inventory',
    'depends': ['stock','product','base', 'web', 'account', 'purchase'],
    'data': [
        'views/product_category_views.xml',
        'views/product_product_views.xml',
        'views/product_template_views.xml',
        'report/account_invoice_document_report.xml',
        'report/base_external_report_layout.xml',
        'report/tax_total_inherit.xml',
        'report/custom_layout.xml',
        'report/delivery_slip_report.xml',

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
