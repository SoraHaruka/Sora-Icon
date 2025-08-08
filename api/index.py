from flask import Flask, request, jsonify, render_template
import requests
import os
import json

app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(__file__), '../static'),
            template_folder=os.path.join(os.path.dirname(__file__), '../templates'))

# PicGo API 和 GitHub Gist 配置
PICGO_API_URL = "https://www.picgo.net/api/1/upload"
PICGO_API_KEY = os.getenv("PICGO_API_KEY", "chv_SwH9j_df309d9dc4f97492e9347b71d94dd589bae19b65cbb282f326e1a99835a06c1e17eba52bdcee02fd1a4c616270ddbf127890194870aaee97c34abd55e49f1f43")  # 替换为你的 PicGo API 密钥
GIST_ID = os.getenv("GIST_ID", "1c8db7ed76ea31c4eef394ecd4cdf105")  # 替换为你的 Gist ID
GITHUB_USER = os.getenv("GITHUB_USER", "SoraHaruka")  # 替换为你的 GITHUB USER
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "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")  # 替换为你的 GitHub Token
GIST_FILE_NAME = "icons.json"


@app.route("/")
def home():
    return render_template("index.html", github_user=GITHUB_USER, gist_id=GIST_ID)


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
            return jsonify({"error": f"图片上传失败: {upload_response.json().get('error').get('message')}",
                            "details": upload_response.text}), upload_response.status_code

        upload_data = upload_response.json()
        image_url = upload_data.get("image").get("url")
        if not image_url:
            return jsonify({"error": "无法获取图片 URL"}), 500

        # 更新 Gist
        gist_result = update_gist(name, image_url)
        if not gist_result["success"]:
            return jsonify({"error": gist_result["error"]}), 400

        return jsonify({"success": True, "name": gist_result["name"]}), 200

    except Exception as e:
        return jsonify({"error": "服务器错误", "details": str(e)}), 500


def get_unique_name(name, json_content):
    """
    检查 json_content["icons"] 中是否已有名称为 name 的图标，
    如果存在重复，则在名称后缀添加递增数字，直到不重复。
    返回唯一名称。
    """
    icons = json_content.get("icons", [])
    if not any(icon["name"] == name for icon in icons):
        return name

    base_name = name
    counter = 1
    while any(icon["name"] == f"{base_name}{counter}" for icon in icons):
        counter += 1
    return f"{base_name}{counter}"


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

    name = get_unique_name(name, json_content)

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

    return {"success": True, "name": name}


if __name__ == "__main__":
    app.run()
