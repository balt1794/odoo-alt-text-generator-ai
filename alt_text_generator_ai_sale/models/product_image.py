# -*- coding: utf-8 -*-
from odoo import _, models


class ProductImage(models.Model):
    _inherit = 'product.image'

    def action_generate_alt_text(self):
        """The shop uses the name of an extra product image as its alt text."""
        client = self.env['alt.text.client']
        generated = 0
        for image in self:
            if image.video_url or not image.image_1920:
                continue
            image.name = client.generate(datas=image.image_1920)
            generated += 1
        if not generated:
            return client._notification(_('Alt text'), _('There was no image to describe.'), 'warning')
        return client._notification(_('Alt text'), _('Alt text added to %s images.', generated))
