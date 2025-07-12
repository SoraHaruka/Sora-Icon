from flask import Flask, request, jsonify, render_template
import requests
import os
import json

app = Flask(__name__)

# PicGo API 和 GitHub Gist 配置
PICGO_API_URL = "https://www.picgo.net/api/1/upload"
PICGO_API_KEY = os.getenv("PICGO_API_KEY", "YOUR_API_KEY")  # 替换为你的 PicGo API 密钥
GIST_ID = os.getenv("GIST_ID", "YOUR_GIST_ID")  # 替换为你的 Gist ID
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN")  # 替换为你的 GitHub Token
GIST_FILE_NAME = "icons.json"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/upload", methods=["POST"])
def upload_image():
    try:
        # 获取表单数据
        image = request.files.get("source")
        name = request.form.get("name")

        if not image or not name:
            return jsonify({"error": "缺少图片或名称"}), 400

        # 上传图片到 PicGo API
        form_data = {"source": (image.filename, image.stream, image.mimetype)}
        headers = {"X-API-Key": PICGO_API_KEY}
        upload_response = requests.post(PICGO_API_URL, files=form_data, headers=headers)

        if upload_response.status_code != 200:
            return jsonify({"error": "图片上传失败", "details": upload_response.text}), upload_response.status_code

        upload_data = upload_response.json()
        image_url = upload_data.get("url")
        if not image_url:
            return jsonify({"error": "无法获取图片 URL"}), 500

        # 更新 Gist
        gist_result = update_gist(name, image_url)
        if not gist_result["success"]:
            return jsonify({"error": gist_result["error"]}), 400

        return jsonify({"success": true, "name": name, "url": image_url}), 200

    except Exception as e:
        return jsonify({"error": "服务器错误", "details": str(e)}), 500

def update_gist(name, url):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    # 获取当前 Gist 内容
    gist_response = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers)
    if gist_response.status_code != 200:
        return {"success": False, "error": "无法获取 Gist"}

    gist_data = gist_response.json()
    try:
        json_content = json.loads(gist_data["files"][GIST_FILE_NAME]["content"])
    except:
        json_content = {"name": "Forward", "description": "", "icons": []}

    # 检查名称是否重复
    if any(icon["name"] == name for icon in json_content["icons"]):
        return {"success": False, "error": "名称已存在"}

    # 添加新图标
    json_content["icons"].append({"name": name, "url": url})

    # 更新 Gist
    update_response = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers=headers,
        json={"files": {GIST_FILE_NAME: {"content": json.dumps(json_content, indent=2)}}},
    )

    if update_response.status_code != 200:
        return {"success": False, "error": "无法更新 Gist"}

    return {"success": True}

if __name__ == "__main__":
    app.run()