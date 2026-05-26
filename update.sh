#!/bin/bash
set -e

echo "=========================================="
echo "  实验室座位考勤系统 - 服务器更新脚本"
echo "=========================================="
echo ""

INSTALL_DIR="/opt/book_seat"
SERVICE_NAME="lab-attendance"

if [ "$EUID" -ne 0 ]; then
  echo "请使用 sudo 运行：sudo bash update.sh"
  exit 1
fi

# 拉取最新代码
echo "[1/4] 拉取最新代码..."
cd "$INSTALL_DIR"
git pull

# 更新后端依赖
echo "[2/4] 更新后端..."
cd "$INSTALL_DIR/backend"
source venv/bin/activate
pip install -q -r requirements.txt
python init_db.py
deactivate
chown -R www-data:www-data "$INSTALL_DIR/backend/"

# 构建前端
echo "[3/4] 构建前端..."
cd "$INSTALL_DIR/frontend"
npm install --silent
npm run build

# 重启服务
echo "[4/4] 重启服务..."
systemctl restart ${SERVICE_NAME}

echo ""
echo "=========================================="
echo "  更新完成！"
echo "=========================================="
