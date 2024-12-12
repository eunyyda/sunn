import requests
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm

# 기상청 API 키
KMA_API_KEY = "2X1K2z0-SHO9Sts9PghzAw"
# Google Maps API 키
GOOGLE_API_KEY = "AIzaSyBV9xHdsunjLlXR6M4DtlAjJ-8k6AOwD2k"

def home(request):
    return render(request, 'home.html')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "회원가입이 완료되었습니다. 로그인해주세요.")
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('weather')
        else:
            messages.error(request, "로그인 정보가 올바르지 않습니다.")
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

def get_coordinates(address):
    """
    Geocoding API를 사용해 주소를 기반으로 위도와 경도를 가져옵니다.
    """
    geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": GOOGLE_API_KEY
    }

    try:
        response = requests.get(geocoding_url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK":
            location = data["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]

        raise ValueError(
            f"Geocoding API 오류: {data.get('status')} - {data.get('error_message', 'No additional information')}")

    except requests.exceptions.RequestException as e:
        raise ValueError(f"API 호출 오류: {e}")

@login_required
def weather(request):
    address = "울산 남구 무거동"  # 주소 입력
    try:
        # Geocoding API를 사용해 위도와 경도 가져오기
        lat, lng = get_coordinates(address)

        # 기상청 API 설정
        weather_api_url = "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getUltraSrtNcst"
        auth_key = "2X1K2z0-SHO9Sts9PghzAw"
        now = datetime.now()
        base_date = now.strftime("%Y%m%d")
        base_time = (now - timedelta(hours=now.hour % 6)).strftime("%H%M")

        weather_params = {
            "pageNo": 1,
            "numOfRows": 1000,
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": 98,
            "ny": 76,
            "authKey": auth_key
        }

        response = requests.get(weather_api_url, params=weather_params, verify=False)
        response.raise_for_status()
        data = response.json()

        category_map = {
            "REH": "습도 (%)",
            "RN1": "1시간 강수량 (mm)",
            "T1H": "기온 (°C)",
            "VEC": "풍향 (deg)",
            "WSD": "풍속 (m/s)"
        }

        if 'response' not in data or 'body' not in data['response']:
            raise ValueError("Invalid API response format")

        items = data['response']['body']['items']['item']
        weather_data = []

        for item in items:
            if item['category'] in category_map:
                weather_data.append({
                    "category": category_map[item['category']],
                    "value": item['obsrValue']
                })

        # 업데이트 시간 표시
        updated_date = f"{base_date[:4]}년 {base_date[4:6]}월 {base_date[6:]}일"
        updated_time = f"{base_time[:2]}시"

        return render(request, 'weather.html', {
            "weather_data": weather_data,
            "location": address,
            "latitude": lat,
            "longitude": lng,
            "updated_datetime": f"{updated_date} {updated_time}"
        })

    except ValueError as e:
        return render(request, 'error.html', {"error": str(e)})
