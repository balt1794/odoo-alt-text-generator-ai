# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

# 1x1 PNG
PIXEL = (
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/'
    'iZk9HQAAAABJRU5ErkJggg=='
)
POST = 'odoo.addons.alt_text_generator_ai.models.alt_text_client.requests.post'


def fake_response(status=200, text='A red pixel on a white background.', credits='41'):
    response = MagicMock()
    response.status_code = status
    response.ok = status < 400
    response.text = text
    response.headers = {'X-Credits-Left': credits}
    return response


@tagged('post_install', '-at_install')
class TestAltText(TransactionCase):

    def setUp(self):
        super().setUp()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('alt_text_generator_ai.api_key', 'test-key')
        params.set_param('alt_text_generator_ai.language', 'spanish')
        self.attachment = self.env['ir.attachment'].create({
            'name': 'pixel.png', 'datas': PIXEL, 'public': True,
        })
        arch = (
            '<t t-name="alt_text_generator_ai.test_page"><t t-call="website.layout">'
            '<div id="wrap"><img src="/web/image/%s"/><img src="/web/image/%s" alt="Has alt"/>'
            '<img src="/web/image/%s" alt=""/></div></t></t>'
        ) % (self.attachment.id, self.attachment.id, self.attachment.id)
        self.view = self.env['ir.ui.view'].create({
            'name': 'Alt text test page', 'type': 'qweb',
            'key': 'alt_text_generator_ai.test_page', 'arch': arch,
        })
        self.page = self.env['website.page'].create({
            'url': '/alt-text-test', 'view_id': self.view.id, 'website_published': True,
        })

    def test_fills_only_missing_alt(self):
        with patch(POST, return_value=fake_response()) as post:
            result = self.page.action_generate_alt_text()
        # one request: both empty images share one source
        self.assertEqual(post.call_count, 1)
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['wpkey'], 'test-key')
        self.assertEqual(payload['language'], 'spanish')
        self.assertTrue(payload['image'].startswith('data:image/png;base64,'))
        arch = self.view.arch
        self.assertEqual(arch.count('A red pixel on a white background.'), 2)
        self.assertIn('alt="Has alt"', arch)
        self.assertEqual(result['params']['type'], 'success')
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_param('alt_text_generator_ai.credits_left'), '41')

    def test_second_run_does_nothing(self):
        with patch(POST, return_value=fake_response()):
            self.page.action_generate_alt_text()
        with patch(POST, return_value=fake_response()) as post:
            result = self.page.action_generate_alt_text()
        self.assertEqual(post.call_count, 0)
        self.assertEqual(result['params']['type'], 'info')

    def test_requires_api_key(self):
        self.env['ir.config_parameter'].sudo().set_param('alt_text_generator_ai.api_key', '')
        with patch(POST) as post, self.assertRaises(UserError):
            self.page.action_generate_alt_text()
        post.assert_not_called()

    def test_api_errors_become_user_errors(self):
        for status in (401, 402, 502):
            with patch(POST, return_value=fake_response(status=status)), self.assertRaises(UserError):
                self.page.action_generate_alt_text()
        self.assertNotIn('A red pixel', self.view.arch)

    def test_fetch_credits(self):
        response = MagicMock(status_code=200, ok=True)
        response.json.return_value = {'freeRewritesLeft': 87}
        with patch(POST, return_value=response) as post:
            credits = self.env['alt.text.client'].fetch_credits()
        self.assertEqual(credits, '87')
        self.assertTrue(post.call_args.args[0].endswith('/api/verify'))
        self.assertEqual(post.call_args.kwargs['json'], {'apiKey': 'test-key'})
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_param('alt_text_generator_ai.credits_left'), '87')
        with patch(POST, return_value=fake_response(status=404)), self.assertRaises(UserError):
            self.env['alt.text.client'].fetch_credits()


@tagged('post_install', '-at_install')
class TestBulkAltText(TestAltText):

    def test_bulk_lists_pages_and_generates(self):
        wizard = self.env['alt.text.bulk'].create({'line_ids': self.env['alt.text.bulk']._scan()})
        lines = wizard.line_ids.filtered(lambda line: line.res_id == self.page.id)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.src, '/web/image/%s' % self.attachment.id)  # the same image twice counts once
        self.assertEqual(lines.thumb_url, lines.src)
        self.assertEqual(wizard.selected_count, len(wizard.line_ids))
        wizard.line_ids.filtered(lambda line: line.id != lines.id).write({'selected': False})
        with patch(POST, return_value=fake_response()):
            wizard.action_generate()
        self.assertEqual(lines.result, 'Done')
        self.assertEqual(lines.alt_text, 'A red pixel on a white background.')
        self.assertFalse(self.page._alt_text_missing_count())

    def test_bulk_stops_when_credits_run_out(self):
        wizard = self.env['alt.text.bulk'].create({'line_ids': self.env['alt.text.bulk']._scan()})
        with patch(POST, return_value=fake_response(status=402)):
            wizard.action_generate()
        self.assertIn('no credits', wizard.summary)
        self.assertTrue(wizard.line_ids.filtered(lambda line: line.result == 'Stopped'))

    def test_bulk_refreshes_credits_when_opened(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('alt_text_generator_ai.credits_left', '0')
        response = MagicMock(status_code=200, ok=True)
        response.json.return_value = {'freeRewritesLeft': 10}
        with patch(POST, return_value=response):
            wizard = self.env['alt.text.bulk'].create({})
            self.env['alt.text.bulk'].default_get(['line_ids'])
        self.assertEqual(wizard.credits_left, '10')

    def test_bulk_can_list_and_rewrite_existing_alt_text(self):
        attachment = self.env['ir.attachment'].create({'name': 'other.png', 'datas': PIXEL, 'public': True})
        view = self.env['ir.ui.view'].create({
            'name': 'Alt text existing page', 'type': 'qweb', 'key': 'alt_text_generator_ai.existing_page',
            'arch': (
                '<t t-name="alt_text_generator_ai.existing_page"><t t-call="website.layout">'
                '<div id="wrap"><img src="/web/image/%s" alt="Old alt"/></div></t></t>'
            ) % attachment.id,
        })
        page = self.env['website.page'].create({'url': '/alt-existing', 'view_id': view.id, 'website_published': True})
        bulk = self.env['alt.text.bulk']
        self.assertFalse([c for c in bulk._scan() if c[2]['res_id'] == page.id])

        lines = [c[2] for c in bulk._scan(include_existing=True) if c[2]['res_id'] == page.id]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['alt_text'], 'Old alt')
        self.assertFalse(lines[0]['selected'])  # nothing is rewritten unless it is ticked
        self.assertTrue(lines[0]['had_alt'])

        wizard = bulk.create({'line_ids': [(0, 0, dict(lines[0], selected=True))]})
        with patch(POST, return_value=fake_response(text='A brand new description.')):
            wizard.action_generate()
        self.assertEqual(page._alt_text_for_src('/web/image/%s' % attachment.id), 'A brand new description.')
