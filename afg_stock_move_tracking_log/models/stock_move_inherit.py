from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup
class StockMove(models.Model):
    _inherit = "stock.move"

    def _format_float(self, value):
        """Clean float precision"""
        try:
            return float(f"{value:.2f}")
        except Exception:
            return value

    def write(self, vals):
        # Store old values before update
        tracked_fields = ["product_uom_qty", "product_id"]
        old_values = {}

        for move in self:
            old_values[move.id] = {
                field: getattr(move, field)
                for field in tracked_fields
                if hasattr(move, field)
            }

        res = super(StockMove, self).write(vals)

        # After update → compare values
        for move in self:
            if not move.picking_id:
                continue

            changes = []

            old_data = old_values.get(move.id, {})

            for field in tracked_fields:
                old_val = old_data.get(field)
                new_val = getattr(move, field, None)

                # Format product field
                if field == "product_id":
                    old_display = old_val.display_name if old_val else ""
                    new_display = new_val.display_name if new_val else ""

                    if old_display != new_display:
                        changes.append(
                            f"<b>Product</b>: {old_display} → {new_display}"
                        )

                # Format float field
                elif field == "product_uom_qty":
                    old_qty = self._format_float(old_val)
                    new_qty = self._format_float(new_val)

                    if old_qty != new_qty:
                        changes.append(
                            f"<b>Quantity</b>: {old_qty} → {new_qty}"
                        )

            # Post message if something changed
            if changes:
                html_body = f"""
                <div>
                    The initial demand has been updated.<br/>
                    <b>[{move.picking_id.name}] {move.product_id.display_name}</b>
                    <br/>
                    {"<br/>".join(changes)}
                </div>
                """

                move.picking_id.message_post(
                    body=Markup(html_body),
                    subtype_xmlid="mail.mt_note"
                )

        return res
