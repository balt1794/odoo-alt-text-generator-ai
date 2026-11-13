# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase, tagged

PIXEL = (
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/'
    'iZk9HQAAAABJRU5ErkJggg=='
)
POST = 'odoo.addons.alt_text_generator_ai.models.alt_text_client.requests.post'


@tagged('post_install', '-at_install')
class TestProductImageAltText(TransactionCase):

    def test_extra_image_name_becomes_alt_text(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('alt_text_generator_ai.api_key', 'test-key')
        template = self.env['product.template'].create({'name': 'Test chair'})
        image = self.env['product.image'].create({
            'name': 'IMG_0001.png', 'image_1920': PIXEL, 'product_tmpl_id': template.id,
        })
        response = MagicMock(status_code=200, ok=True, text='A single red pixel.', headers={})
        with patch(POST, return_value=response):
            image.action_generate_alt_text()
        self.assertEqual(image.name, 'A single red pixel.')
