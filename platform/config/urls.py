from django.urls import path, include
from django.contrib.auth import views as auth
from core import views as v, public_views as p, auth_views as a
from documents.views import download, public_image
from core import admin_views as admin
from admissions import admin_views as admission_admin
from team import views as team_views
from core.report_views import survey_export
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path("i18n/js/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("staff/<slug:slug>/survey-export/", survey_export, name="survey-export"),
    path("accounts/recover/", a.recover_password, name="password-recover"),
    path("e/<slug:slug>/volunteer-access/<str:raw>/", team_views.access, name="volunteer-access"),
    path("e/<slug:slug>/volunteer-recovery/", team_views.recover, name="volunteer-recover"),
    path("", p.home, name="home"),
    path("health/", v.health),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/login/", a.LoginView.as_view(), name="login"),
    path("accounts/development-login/", a.development_login, name="development-login"),
    path("accounts/logout/", auth.LogoutView.as_view(), name="logout"),
    path("accounts/mfa/", a.mfa, name="mfa"),
    path("accounts/mfa/qr/", a.mfa_qr, name="mfa-qr"),
    path(
        "accounts/password/",
        auth.PasswordChangeView.as_view(template_name="registration/password_form.html"),
        name="password_change",
    ),
    path(
        "accounts/password/done/",
        auth.PasswordChangeDoneView.as_view(template_name="registration/password_done.html"),
        name="password_change_done",
    ),
    path(
        "accounts/reset/<uidb64>/<token>/",
        auth.PasswordResetConfirmView.as_view(template_name="registration/password_form.html"),
        name="password_reset_confirm",
    ),
    path(
        "accounts/reset/done/",
        auth.PasswordResetCompleteView.as_view(template_name="registration/password_done.html"),
        name="password_reset_complete",
    ),
    path("e/<slug:slug>/register/", p.register, name="register"),
    path("e/<slug:slug>/volunteer/", p.volunteer, name="volunteer-apply"),
    path("e/<slug:slug>/recover/", p.recover, name="recover"),
    path("e/<slug:slug>/access/<str:raw>/", p.access, name="ticket-access"),
    path("e/<slug:slug>/access/<str:raw>/qr/", p.ticket_qr, name="ticket-qr"),
    path("e/<slug:slug>/speakers/<uuid:pk>/", p.speaker, name="speaker"),
    path("e/<slug:slug>/<slug:key>/", p.page, name="public-page"),
    path("e/<slug:slug>/images/<uuid:pk>/", public_image, name="public-image"),
    path("staff/", v.staff_home, name="staff-home"),
    path("staff/<slug:slug>/", v.dashboard, name="dashboard"),
    path("staff/<slug:slug>/settings/", v.event_settings, name="event-settings"),
    path("staff/<slug:slug>/workspace/<slug:group>/", v.workspace_group, name="workspace-group"),
    path("staff/<slug:slug>/speakers/<uuid:pk>/photo/", v.speaker_photo, name="speaker-photo"),
    path("staff/<slug:slug>/users/", admin.users, name="users"),
    path("staff/<slug:slug>/users/invite/", admin.invite_user, name="invite-user"),
    path("staff/<slug:slug>/preview/", admin.preview, name="preview"),
    path("staff/<slug:slug>/imports/", admission_admin.imports, name="imports"),
    path("staff/<slug:slug>/imports/<uuid:pk>/", admission_admin.import_review, name="import-review"),
    path("staff/<slug:slug>/roster/", admission_admin.roster, name="roster"),
    path("staff/<slug:slug>/check-in/", v.scanner, name="scanner"),
    path("staff/<slug:slug>/check-in/data/", v.scanner_data, name="scanner-data"),
    path("staff/<slug:slug>/check-in/scan/", v.scan_api, name="scan-api"),
    path("staff/<slug:slug>/entry-mode/", v.entry_mode, name="entry-mode"),
    path("staff/<slug:slug>/reports/", v.reports, name="reports"),
    path("staff/<slug:slug>/files/<uuid:pk>/download/", download, name="file-download"),
    path("staff/<slug:slug>/<slug:key>/", v.resource_list, name="resource-list"),
    path("staff/<slug:slug>/<slug:key>/new/", v.resource_edit, name="resource-create"),
    path("staff/<slug:slug>/<slug:key>/export/", v.export, name="resource-export"),
    path("staff/<slug:slug>/<slug:key>/<uuid:pk>/", v.resource_detail, name="resource-detail"),
    path("staff/<slug:slug>/<slug:key>/<uuid:pk>/edit/", v.resource_edit, name="resource-edit"),
    path("staff/<slug:slug>/<slug:key>/<uuid:pk>/comment/", v.comment, name="comment"),
    path("staff/<slug:slug>/<slug:key>/<uuid:pk>/<slug:action>/", v.resource_action, name="resource-action"),
]
