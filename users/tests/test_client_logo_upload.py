"""
Tests for POST /api/admin/clients/<id>/upload-logo/.

Covers:
  • valid PNG / JPEG / GIF / WebP magic bytes accepted
  • bogus extensions rejected (sniffed by content, not name)
  • SVG rejected (security: SVG can carry <script>)
  • size cap enforced
  • only the owning tenant can upload to their own client
  • returned URL is absolute and the Client row is updated
"""
import io
import os
import shutil
import tempfile

import pytest
from django.urls import reverse


def _png_bytes():
    """Minimal valid 1x1 PNG (89 bytes)."""
    return (
        b'\x89PNG\r\n\x1a\n'
        b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        b'\x00\x00\x00\rIDATx\x9cc\xfc\xcf\xc0P\x0f\x00\x00\x05\x00\x01\xe2&\x05\x9b\x00\x00\x00\x00IEND\xaeB`\x82'
    )


def _jpeg_bytes():
    """Minimal-looking JPEG header — enough to pass the magic sniff."""
    return b'\xff\xd8\xff\xe0' + b'\x00' * 64


def _gif_bytes():
    return b'GIF89a' + b'\x00' * 32


def _webp_bytes():
    # RIFF....WEBP — sniff only checks first 12 bytes.
    return b'RIFF\x00\x00\x00\x00WEBP' + b'\x00' * 64


def _svg_bytes():
    return b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


@pytest.fixture
def temp_media(settings, tmp_path):
    """Point MEDIA_ROOT at a per-test tmpdir so uploads don't leak."""
    media = tmp_path / 'media'
    media.mkdir()
    settings.MEDIA_ROOT = str(media)
    settings.MEDIA_URL = '/media/'
    yield str(media)


def _upload_url(client_id):
    return f'/api/admin/clients/{client_id}/upload-logo/'


@pytest.mark.django_db
class TestUploadClientLogoHappyPath:
    def test_png_upload_succeeds(self, tenant_client, tenant_user, client_obj, temp_media):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('logo.png', _png_bytes(), content_type='image/png')
        resp = tenant_client.post(_upload_url(client_obj.id), {'logo': f}, format='multipart')

        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body['logo_url'].endswith('.png')
        assert body['logo_url'] == body['chatbot_logo_url']
        # Persisted to the Client
        client_obj.refresh_from_db()
        assert client_obj.chatbot_logo_url == body['logo_url']
        # File actually written
        rel = body['logo_url'].split('/media/', 1)[1]
        assert os.path.isfile(os.path.join(temp_media, rel))

    def test_jpeg_upload_succeeds(self, tenant_client, client_obj, temp_media):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('photo.jpg', _jpeg_bytes(), content_type='image/jpeg')
        resp = tenant_client.post(_upload_url(client_obj.id), {'logo': f}, format='multipart')
        assert resp.status_code == 200
        assert resp.json()['logo_url'].endswith('.jpg')

    def test_gif_upload_succeeds(self, tenant_client, client_obj, temp_media):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('logo.gif', _gif_bytes(), content_type='image/gif')
        resp = tenant_client.post(_upload_url(client_obj.id), {'logo': f}, format='multipart')
        assert resp.status_code == 200
        assert resp.json()['logo_url'].endswith('.gif')

    def test_webp_upload_succeeds(self, tenant_client, client_obj, temp_media):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('logo.webp', _webp_bytes(), content_type='image/webp')
        resp = tenant_client.post(_upload_url(client_obj.id), {'logo': f}, format='multipart')
        assert resp.status_code == 200
        assert resp.json()['logo_url'].endswith('.webp')


@pytest.mark.django_db
class TestUploadClientLogoValidation:
    def test_missing_file_returns_400(self, tenant_client, client_obj, temp_media):
        resp = tenant_client.post(_upload_url(client_obj.id), {}, format='multipart')
        assert resp.status_code == 400

    def test_svg_is_rejected(self, tenant_client, client_obj, temp_media):
        """SVG can carry <script> — must NOT be accepted even with image/svg+xml MIME."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('logo.svg', _svg_bytes(), content_type='image/svg+xml')
        resp = tenant_client.post(_upload_url(client_obj.id), {'logo': f}, format='multipart')
        assert resp.status_code == 400
        assert 'Unsupported' in resp.json()['detail']

    def test_renamed_exe_is_rejected(self, tenant_client, client_obj, temp_media):
        """Magic-byte sniff must catch a bogus file with .png extension."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('evil.png', b'MZ\x90\x00' + b'\x00' * 32, content_type='image/png')
        resp = tenant_client.post(_upload_url(client_obj.id), {'logo': f}, format='multipart')
        assert resp.status_code == 400

    def test_oversize_rejected(self, tenant_client, client_obj, temp_media):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from users.admin_views import _LOGO_MAX_BYTES
        # PNG header + filler past the cap
        body = _png_bytes() + b'\x00' * (_LOGO_MAX_BYTES + 16)
        f = SimpleUploadedFile('huge.png', body, content_type='image/png')
        resp = tenant_client.post(_upload_url(client_obj.id), {'logo': f}, format='multipart')
        assert resp.status_code == 400
        assert 'too large' in resp.json()['detail'].lower()


@pytest.mark.django_db
class TestUploadClientLogoOwnership:
    def test_other_tenant_cannot_upload(self, tenant_client2, client_obj, temp_media):
        """tenant_client2 has its own client; client_obj belongs to tenant_user."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('logo.png', _png_bytes(), content_type='image/png')
        resp = tenant_client2.post(_upload_url(client_obj.id), {'logo': f}, format='multipart')
        assert resp.status_code == 404  # get_accessible_clients filters it out

    def test_anonymous_cannot_upload(self, anon_client, client_obj, temp_media):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('logo.png', _png_bytes(), content_type='image/png')
        resp = anon_client.post(_upload_url(client_obj.id), {'logo': f}, format='multipart')
        assert resp.status_code == 401

    def test_superadmin_can_upload(self, superadmin_client, client_obj, temp_media):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('logo.png', _png_bytes(), content_type='image/png')
        resp = superadmin_client.post(_upload_url(client_obj.id), {'logo': f}, format='multipart')
        assert resp.status_code == 200


@pytest.mark.django_db
class TestUploadClientLogoStorage:
    def test_url_is_absolute(self, tenant_client, client_obj, temp_media):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('logo.png', _png_bytes(), content_type='image/png')
        resp = tenant_client.post(_upload_url(client_obj.id), {'logo': f}, format='multipart')
        url = resp.json()['logo_url']
        assert url.startswith('http://') or url.startswith('https://')
        assert '/media/client_logos/' in url

    def test_files_are_isolated_per_client(self, tenant_client, client_obj, temp_media):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('logo.png', _png_bytes(), content_type='image/png')
        tenant_client.post(_upload_url(client_obj.id), {'logo': f}, format='multipart')
        # Folder named after the client ID exists
        client_dir = os.path.join(temp_media, 'client_logos', str(client_obj.id))
        assert os.path.isdir(client_dir)
        # And contains exactly one file
        assert len(os.listdir(client_dir)) == 1
