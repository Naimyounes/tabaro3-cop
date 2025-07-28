from firebase_functions import https_fn
from flask import Flask, redirect, request
from app import app as flask_app

@https_fn.on_request()
def app(req: https_fn.Request) -> https_fn.Response:
    # معالجة الطلب باستخدام تطبيق Flask
    with flask_app.request_context(req.environ):
        try:
            response = flask_app.full_dispatch_request()
            return response
        except Exception as e:
            return https_fn.Response(f"خطأ: {str(e)}", status=500)