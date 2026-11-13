# -*- coding: utf-8 -*-
import base64
import logging

import requests

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.image import image_process
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://alttextgeneratorai.com/api/odoo'
SUPPORTED_MIMETYPES = ('image/jpeg', 'image/png', 'image/gif', 'image/webp')
# The API accepts data URLs up to 6,000,000 characters.
MAX_DATA_URL_LENGTH = 5_500_000
RESIZE_STEPS = (1600, 1024, 640)


class AltTextClient(models.AbstractModel):
    _name = 'alt.text.client'
    _description = 'Alt Text Generator AI client'

    @api.model
    def _get_settings(self):
        params = self.env['ir.config_parameter'].sudo()
        return {
            'api_key': (params.get_param('alt_text_generator_ai.api_key') or '').strip(),
            'language': (params.get_param('alt_text_generator_ai.language') or 'english').strip().lower(),
            'endpoint': (params.get_param('alt_text_generator_ai.endpoint') or DEFAULT_ENDPOINT).strip(),
        }

    @api.model
    def _to_data_url(self, datas):
        """Return a data URL for base64 image `datas`, shrunk to fit the API limit."""
        raw = base64.b64decode(datas)
        mimetype = guess_mimetype(raw)
        if mimetype not in SUPPORTED_MIMETYPES:
            raise UserError(_('Unsupported image type: %s. Use JPEG, PNG, GIF or WebP.', mimetype))
        for size in RESIZE_STEPS:
            try:
                processed = image_process(datas, size=(size, size), quality=85) or datas
            except Exception:  # noqa: BLE001 - fall back to the original bytes
                _logger.warning('Could not resize an image before sending it', exc_info=True)
                processed = datas
            if isinstance(processed, bytes):
                processed = processed.decode()
            data_url = 'data:%s;base64,%s' % (mimetype, processed)
            if len(data_url) <= MAX_DATA_URL_LENGTH:
                return data_url
        raise UserError(_('This image is too large to send.'))

    @api.model
    def generate(self, datas=None, url=None):
        """Generate alt text for a base64 image (`datas`) or a public image `url`."""
        settings = self._get_settings()
        if not settings['api_key']:
            raise UserError(_('Add your AltTextGeneratorAI API key in Settings > Alt Text Generator AI.'))
        if datas:
            image = self._to_data_url(datas)
        elif url:
            image = url
        else:
            raise UserError(_('There is no image to describe.'))

        try:
            response = requests.post(
                settings['endpoint'],
                json={'image': image, 'wpkey': settings['api_key'], 'language': settings['language']},
                timeout=90,
            )
        except requests.RequestException as error:
            _logger.warning('Alt Text Generator AI request failed: %s', error)
            raise UserError(_('Could not reach alttextgeneratorai.com. Check your connection and try again.'))

        if response.status_code == 401:
            raise UserError(_('The API key is not valid. Check it in Settings > Alt Text Generator AI.'))
        if response.status_code == 402:
            raise UserError(_('You have no credits left. Get more at https://alttextgeneratorai.com/pricing'))
        if not response.ok:
            raise UserError(_('Alt text could not be generated (error %s).', response.status_code))

        credits_left = response.headers.get('X-Credits-Left')
        if credits_left is not None:
            self.env['ir.config_parameter'].sudo().set_param('alt_text_generator_ai.credits_left', credits_left)
        return response.text.strip().strip('"\'').strip()

    @api.model
    def fetch_credits(self):
        """Read the credits left for the saved API key (no image is sent) and remember them."""
        settings = self._get_settings()
        if not settings['api_key']:
            raise UserError(_('Add your AltTextGeneratorAI API key first.'))
        verify_url = settings['endpoint'].rsplit('/api/', 1)[0] + '/api/verify'
        try:
            response = requests.post(verify_url, json={'apiKey': settings['api_key']}, timeout=30)
        except requests.RequestException as error:
            _logger.warning('Alt Text Generator AI balance request failed: %s', error)
            raise UserError(_('Could not reach alttextgeneratorai.com. Check your connection and try again.'))
        if response.status_code == 404:
            raise UserError(_('The API key is not valid. Check it in Settings > Alt Text Generator AI.'))
        if not response.ok:
            raise UserError(_('The credits could not be read (error %s).', response.status_code))
        credits_left = str(response.json().get('freeRewritesLeft', ''))
        self.env['ir.config_parameter'].sudo().set_param('alt_text_generator_ai.credits_left', credits_left)
        return credits_left

    @api.model
    def _notification(self, title, message, notification_type='success', sticky=False):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notification_type,
                'sticky': sticky,
            },
        }
