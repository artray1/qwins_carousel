from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils.timezone import now
from datetime import timedelta
from .models import *
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import requests, uuid, xml.etree.ElementTree as ET
import random
import string


def generate_unique_promocode(length=15):
    for _ in range(10):
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not Promocode.objects.filter(code=code).exists():
            return code
    raise Exception("Cannot generate unique promocode")


def choose_random_prize():
    prizes = Prize.objects.all()
    choices = list(prizes)
    weights = [prize.drop_chance for prize in choices]
    return random.choices(choices, weights=weights, k=1)[0]


@csrf_exempt
def login(request):
    if request.method == "GET":
        session_token = request.COOKIES.get("session_token")
        if session_token:
            try:
                session = BillTokenSession.objects.get(
                    session_token=session_token, expires_at__gte=now()
                )
                return JsonResponse(get_user_data(session.username))
            except BillTokenSession.DoesNotExist:
                pass
        return JsonResponse({"authenticated": False}, status=401)

    if request.method == "POST":
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return JsonResponse({"error": "No credentials provided"}, status=401)

        resp = requests.get(
            "https://my.qwins.co/billmgr",
            params={
                "out": "xml",
                "func": "auth",
                "username": username,
                "password": password,
            },
            verify=False,
        )

        root = ET.fromstring(resp.text)
        auth_tag = root.find("auth")
        bill_token = auth_tag.text if auth_tag is not None else None

        if not bill_token:
            return JsonResponse({"error": "Invalid credentials"}, status=401)

        new_token = str(uuid.uuid4())
        expires = now() + timedelta(hours=1)

        BillTokenSession.objects.update_or_create(
            username=username,
            defaults={
                "session_token": new_token,
                "bill_token": bill_token,
                "expires_at": expires,
            },
        )

        UserProfile.objects.get_or_create(username=username)

        response = JsonResponse(get_user_data(username))
        response.set_cookie(
            "session_token",
            new_token,
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=3600,
        )
        return response

    return JsonResponse({"error": "Invalid method"}, status=405)


def get_user_servers(bill_token: str) -> dict:
    url = "https://my.qwins.co/billmgr"
    targets = {"vds": "Виртуальные серверы", "dedic": "Выделенные серверы"}
    result = {}

    for func, title in targets.items():
        params = {
            "out": "xml",
            "func": func,
            "auth": bill_token,
        }

        try:
            response = requests.get(url, params=params, verify=False)
            response.raise_for_status()  # выбросит исключение при коде ответа 4xx/5xx
            root = ET.fromstring(response.text)
            elems = root.findall("elem")

            result[func] = []

            for elem in elems:
                id_ = elem.get("id")
                name = elem.get("name") or elem.get("hostname") or "(без имени)"
                state = elem.get("state") or "-"
                result[func].append({"id": id_, "name": name, "state": state})

        except Exception as e:
            result[func] = {"error": str(e)}

    print("bill_token:", bill_token)
    print("servers_list:", result)
    return result


def get_user_data(username):
    promocodes = Promocode.objects.filter(username=username)
    promo_data = [{"code": p.code, "prize": p.prize} for p in promocodes]

    solved_tasks = SolvedTask.objects.filter(username=username).select_related("task")
    solved_dict = {s.task_id: s.completed_at for s in solved_tasks}

    tasks = Task.objects.all()
    task_data = [
        {
            "id": task.id,
            "title": task.title,
            "reward": task.reward,
            "completed": task.id in solved_dict,
            "completed_at": (
                solved_dict[task.id].isoformat() if task.id in solved_dict else None
            ),
            "svg": task.svg,
            "text": task.text,
            "action_url": task.action_url,
        }
        for task in tasks
    ]

    profile = UserProfile.objects.get(username=username)

    return {
        "authenticated": True,
        "username": username,
        "promocodes": promo_data,
        "tasks": task_data,
        "tickets": profile.tickets,
    }


@csrf_exempt
def complete_task(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    session_token = request.COOKIES.get("session_token")
    if not session_token:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        session = BillTokenSession.objects.get(
            session_token=session_token, expires_at__gte=now()
        )
    except BillTokenSession.DoesNotExist:
        return JsonResponse({"error": "Session expired"}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    task_id = data.get("task_id")
    if not task_id:
        return JsonResponse({"error": "No task_id provided"}, status=400)

    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        return JsonResponse({"error": "Invalid task_id"}, status=404)

    username = session.username
    if SolvedTask.objects.filter(username=username, task=task).exists():
        return JsonResponse({"error": "Already completed"}, status=409)

    if task.id == "buy_server":
        servers = get_user_servers(session.bill_token)
        for _, servers in servers.items():
            if isinstance(servers, list) and len(servers) > 0:
                break
        else:
            return JsonResponse({"error": "Task not completed"}, status=409)

    SolvedTask.objects.create(username=username, task=task)
    profile = UserProfile.objects.get(username=username)
    profile.tickets += task.reward
    profile.save()

    user_data = get_user_data(username)
    user_data["message"] = "Task completed"
    return JsonResponse(user_data)


@csrf_exempt
def spin_wheel(request):
    if request.method == "POST":
        session_token = request.COOKIES.get("session_token")
        if not session_token:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        try:
            session = BillTokenSession.objects.get(
                session_token=session_token, expires_at__gte=now()
            )
        except BillTokenSession.DoesNotExist:
            return JsonResponse({"error": "Session expired"}, status=401)

        username = session.username
        profile = UserProfile.objects.get(username=username)

        if profile.tickets <= 0:
            return JsonResponse({"error": "Not enough tickets"}, status=403)

        prize = choose_random_prize()
        code = generate_unique_promocode()

        Promocode.objects.create(username=username, code=code, prize=prize.id)
        profile.tickets -= 1
        profile.save()

        print(
            {
                "code": code,
                "prize": prize.id,
                "tickets": profile.tickets,
            }
        )

        return JsonResponse(
            {
                "code": code,
                "prize": prize.id,
                "tickets": profile.tickets,
            }
        )
