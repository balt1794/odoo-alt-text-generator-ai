# -*- coding: utf-8 -*-
import logging

from odoo import fields, models
from odoo.exceptions import UserError

from .languages import LANGUAGES

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    alt_text_ai_api_key = fields.Char(
        string='API Key',
        config_parameter='alt_text_generator_ai.api_key',
        help='Your AltTextGeneratorAI API key. Get a free one at '
             'https://alttextgeneratorai.com/dashboard',
    )
    alt_text_ai_language = fields.Selection(
        LANGUAGES,
        string='Language',
        config_parameter='alt_text_generator_ai.language',
        default='english',
    )
    alt_text_ai_credits_left = fields.Char(
        string='Credits left',
        config_parameter='alt_text_generator_ai.credits_left',
        readonly=True,
    )

    def set_values(self):
        super().set_values()
        # Show the balance right after the key is saved. A failure here must not block saving.
        if self.alt_text_ai_api_key:
            try:
                self.env['alt.text.client'].fetch_credits()
            except UserError:
                _logger.info('Could not read the Alt Text Generator AI balance after saving settings')

    def action_alt_text_get_credits(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://alttextgeneratorai.com/pricing',
            'target': 'new',
        }

    def action_alt_text_refresh_credits(self):
        self.env['alt.text.client'].fetch_credits()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
