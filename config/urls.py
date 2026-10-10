from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.static import serve
from django.urls import re_path
from django.http import Http404
import posixpath


def servir_media(request, path, document_root=None):
    # Les CV (media/candidatures/) ne sont jamais servis publiquement :
    # l'équipe les télécharge depuis l'admin (vitrine.views.cv_candidature).
    normalise = posixpath.normpath(path.replace("\\", "/")).lstrip("/")
    if normalise.split("/", 1)[0].lower() == "candidatures":
        raise Http404
    return serve(request, path, document_root=document_root)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("vitrine.urls")),
    re_path(r'^media/(?P<path>.*)$', servir_media, {'document_root': settings.MEDIA_ROOT}),
]
