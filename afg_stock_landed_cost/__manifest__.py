{
    "name": "AFG Stock landed costs",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "description": """AFG Landed Cost""",
    "website": "",
    "author": "Priya, Rhodes technologies Ltd",
    "license": "AGPL-3",
    "depends": [
        "stock_landed_costs",
        "report_xlsx",
    ],
    "data": [
        "security/approve_security.xml",
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "views/stock_landed_cost_views.xml",
        "views/product_views.xml",
        "wizards/wizard_message_view.xml",
        "report/menu_landed_cost_xlsx.xml"
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
