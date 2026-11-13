# -*- coding: utf-8 -*-
import re

from odoo import _, api, models

# Extra product images keep their file name until alt text is written into the name.
FILE_NAME = re.compile(r'(\.(jpe?g|png|gif|webp|bmp|svg)$)|(^(img|dsc|dcim|image|photo)[-_ ]?\d+)', re.I)


class AltTextBulk(models.TransientModel):
    _inherit = 'alt.text.bulk'

    @api.model
    def _scan(self, include_existing=False):
        commands = super()._scan(include_existing=include_existing)
        for image in self.env['product.image'].search([]):
            if image.video_url:
                continue
            has_alt = bool(image.name) and not FILE_NAME.search(image.name)
            if has_alt and not include_existing:
                continue
            commands.append((0, 0, {
                'kind': _('Product image'),
                'res_model': 'product.image',
                'res_id': image.id,
                'name': '%s - %s' % (image.product_tmpl_id.name, image.name or ''),
                'thumb_url': '/web/image/product.image/%s/image_256' % image.id,
                'had_alt': has_alt,
                'selected': not has_alt,
                'alt_text': image.name if has_alt else False,
            }))
        return commands
