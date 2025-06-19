from django.urls import path
from . import views
from .side_views import auth_views, questionnaire_views

urlpatterns = [
    path("", auth_views.index, name="index"),
    path("signup/", auth_views.signup, name="signup"), # http://127.0.0.1:8000/api/signup
    path("login/", auth_views.login, name="login"),
    path("change-password/", auth_views.change_password, name="change_password"),
    path("upload_model/", views.upload_model, name="upload_model"),
    path("getmetadata/<str:network_id>", views.get_metadata, name="getmetadata"),
    path("predict/", views.predict, name="predict"),
    path("predict_MPE/", views.predict_MPE, name="predict_MPE"),
    path("networks/", views.get_networks, name="get_networks"),
    path("submit_answers/", questionnaire_views.submit_answers, name="submit_answers"),
    path("get_answers/", questionnaire_views.get_answers_by_question, name="get_answers"),
    path("create_questionnaire/", questionnaire_views.create_questionnaire, name="create_questionnaire"),
    path("create_question/", questionnaire_views.create_question, name="create_question"),
    path("get_questions/", questionnaire_views.get_questions_by_questionnaire, name="get_questions"),
    path("download_answers_csv/", questionnaire_views.download_answers_csv, name="download_answers_csv"),
]


