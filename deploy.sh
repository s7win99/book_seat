#!/bin/bash
set -e

echo "=========================================="
echo "  实验室座位考勤系统 - 一键部署脚本"
echo "=========================================="
echo ""

# 配置
REPO_URL="https://github.com/s7win99/book_seat.git"
INSTALL_DIR="/opt/book_seat"
SERVICE_NAME="lab-attendance"

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
  echo "请使用 sudo 运行此脚本：sudo bash deploy.sh"
  exit 1
fi

# 安装系统依赖
echo "[1/6] 安装系统依赖..."
if command -v apt-get &> /dev/null; then
  apt-get update -qq
  apt-get install -y -qq python3 python3-pip python3-venv nodejs npm nginx git
elif command -v yum &> /dev/null; then
  yum install -y python3 python3-pip nodejs npm nginx git
else
  echo "不支持的包管理器，请手动安装：python3, pip, nodejs, npm, nginx, git"
  exit 1
fi

# 克隆代码
echo "[2/6] 克隆代码..."
if [ -d "$INSTALL_DIR" ]; then
  cd "$INSTALL_DIR"
  git pull
else
  git clone "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# 安装后端依赖
echo "[3/6] 安装后端依赖..."
cd "$INSTALL_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# 构建前端
echo "[4/6] 构建前端..."
cd "$INSTALL_DIR/frontend"
npm install --silent
npm run build

# 创建 systemd 服务
echo "[5/6] 配置系统服务..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Lab Attendance Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=${INSTALL_DIR}/backend
ExecStart=${INSTALL_DIR}/backend/venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

# 配置 Nginx
echo "[6/6] 配置 Nginx..."
SERVER_IP=$(hostname -I | awk '{print $1}')

cat > /etc/nginx/sites-available/${SERVICE_NAME} << EOF
server {
    listen 80;
    server_name ${SERVER_IP};

    location / {
        root ${INSTALL_DIR}/frontend/dist;
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  访问地址：http://${SERVER_IP}"
echo "  管理员账号：admin"
echo "  管理员密码：admin123"
echo ""
echo "  后端状态：systemctl status ${SERVICE_NAME}"
echo "  查看日志：journalctl -u ${SERVICE_NAME} -f"
echo "  数据库位置：${INSTALL_DIR}/backend/lab_attendance.db"
echo ""
