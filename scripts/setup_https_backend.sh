#!/bin/bash

# EC2 백엔드에 HTTPS 설정하는 스크립트
# nginx를 사용하여 FastAPI 백엔드를 HTTPS로 프록시

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔒 EC2 백엔드 HTTPS 설정 시작...${NC}"

# 1. nginx 설치 확인 및 설치
echo -e "${YELLOW}📦 nginx 설치 확인...${NC}"
if ! command -v nginx &> /dev/null; then
    echo "nginx가 설치되어 있지 않습니다. 설치 중..."
    sudo apt update
    sudo apt install -y nginx
    echo -e "${GREEN}✅ nginx 설치 완료${NC}"
else
    echo -e "${GREEN}✅ nginx가 이미 설치되어 있습니다${NC}"
fi

# 2. certbot 설치 확인 및 설치
echo -e "${YELLOW}📦 certbot 설치 확인...${NC}"
if ! command -v certbot &> /dev/null; then
    echo "certbot이 설치되어 있지 않습니다. 설치 중..."
    sudo apt install -y certbot python3-certbot-nginx
    echo -e "${GREEN}✅ certbot 설치 완료${NC}"
else
    echo -e "${GREEN}✅ certbot이 이미 설치되어 있습니다${NC}"
fi

# 3. 도메인 이름 확인
echo -e "${YELLOW}🌐 도메인 설정...${NC}"
read -p "백엔드 도메인 이름을 입력하세요 (예: api.devictoria.shop 또는 ec2-13-124-217-222.ap-northeast-2.compute.amazonaws.com): " DOMAIN_NAME

if [ -z "$DOMAIN_NAME" ]; then
    echo -e "${RED}❌ 도메인 이름이 필요합니다${NC}"
    exit 1
fi

# 4. nginx 기본 설정 파일 백업
echo -e "${YELLOW}📝 nginx 설정 파일 생성...${NC}"
NGINX_CONF="/etc/nginx/sites-available/langchain-backend"
sudo tee "$NGINX_CONF" > /dev/null <<EOF
# LangChain Backend HTTPS Proxy
server {
    listen 80;
    server_name $DOMAIN_NAME;

    # Let's Encrypt 인증을 위한 임시 설정
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # HTTP에서 HTTPS로 리다이렉트 (SSL 인증서 발급 후 활성화)
    # location / {
    #     return 301 https://\$server_name\$request_uri;
    # }
    
    # 임시로 HTTP 프록시 (SSL 인증서 발급 전까지)
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # CORS 헤더 추가
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
        
        if (\$request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE';
            add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization';
            add_header 'Access-Control-Max-Age' 1728000;
            add_header 'Content-Type' 'text/plain; charset=utf-8';
            add_header 'Content-Length' 0;
            return 204;
        }
    }
}

# HTTPS 설정 (SSL 인증서 발급 후 자동으로 추가됨)
# server {
#     listen 443 ssl http2;
#     server_name $DOMAIN_NAME;
#
#     ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
#     ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;
#     ssl_protocols TLSv1.2 TLSv1.3;
#     ssl_ciphers HIGH:!aNULL:!MD5;
#
#     location / {
#         proxy_pass http://localhost:8000;
#         proxy_set_header Host \$host;
#         proxy_set_header X-Real-IP \$remote_addr;
#         proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto \$scheme;
#         
#         # CORS 헤더
#         add_header 'Access-Control-Allow-Origin' '*' always;
#         add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE' always;
#         add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
#         
#         if (\$request_method = 'OPTIONS') {
#             add_header 'Access-Control-Allow-Origin' '*';
#             add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE';
#             add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization';
#             add_header 'Access-Control-Max-Age' 1728000;
#             add_header 'Content-Type' 'text/plain; charset=utf-8';
#             add_header 'Content-Length' 0;
#             return 204;
#         }
#     }
# }
EOF

# 5. nginx 사이트 활성화
echo -e "${YELLOW}🔗 nginx 사이트 활성화...${NC}"
sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default  # 기본 사이트 비활성화 (선택사항)

# 6. nginx 설정 테스트
echo -e "${YELLOW}🧪 nginx 설정 테스트...${NC}"
if sudo nginx -t; then
    echo -e "${GREEN}✅ nginx 설정이 올바릅니다${NC}"
else
    echo -e "${RED}❌ nginx 설정에 오류가 있습니다${NC}"
    exit 1
fi

# 7. nginx 재시작
echo -e "${YELLOW}🔄 nginx 재시작...${NC}"
sudo systemctl restart nginx
sudo systemctl enable nginx
echo -e "${GREEN}✅ nginx 재시작 완료${NC}"

# 8. EC2 보안 그룹 확인 안내
echo -e "${BLUE}📋 EC2 보안 그룹 확인 필요:${NC}"
echo "   - 포트 80 (HTTP)이 열려있어야 합니다"
echo "   - 포트 443 (HTTPS)이 열려있어야 합니다"
echo "   - AWS 콘솔 → EC2 → Security Groups에서 확인하세요"

# 9. DNS 설정 안내
echo -e "${BLUE}📋 DNS 설정 확인:${NC}"
echo "   - 도메인 $DOMAIN_NAME이 이 EC2 인스턴스의 공개 IP를 가리켜야 합니다"
echo "   - Route 53 또는 도메인 제공업체에서 A 레코드 설정"

# 10. SSL 인증서 발급 옵션
echo ""
echo -e "${YELLOW}🔐 SSL 인증서 발급 옵션:${NC}"
echo ""
echo "옵션 1: Let's Encrypt 자동 발급 (권장)"
echo "  sudo certbot --nginx -d $DOMAIN_NAME"
echo ""
echo "옵션 2: 수동 발급"
echo "  sudo certbot certonly --nginx -d $DOMAIN_NAME"
echo ""
read -p "지금 SSL 인증서를 발급하시겠습니까? (y/n): " ISSUE_SSL

if [ "$ISSUE_SSL" = "y" ] || [ "$ISSUE_SSL" = "Y" ]; then
    echo -e "${YELLOW}🔐 SSL 인증서 발급 중...${NC}"
    echo "이메일 주소를 입력하세요 (Let's Encrypt 알림용):"
    read -p "이메일: " EMAIL
    
    if [ -z "$EMAIL" ]; then
        EMAIL="admin@$DOMAIN_NAME"
    fi
    
    sudo certbot --nginx -d "$DOMAIN_NAME" --email "$EMAIL" --agree-tos --non-interactive || {
        echo -e "${RED}❌ SSL 인증서 발급 실패${NC}"
        echo "다음 사항을 확인하세요:"
        echo "  1. 도메인이 EC2 IP를 가리키고 있는지"
        echo "  2. 포트 80이 열려있는지"
        echo "  3. nginx가 실행 중인지"
        exit 1
    }
    
    echo -e "${GREEN}✅ SSL 인증서 발급 완료!${NC}"
    echo -e "${GREEN}✅ HTTPS가 활성화되었습니다: https://$DOMAIN_NAME${NC}"
else
    echo -e "${YELLOW}⏭️  SSL 인증서 발급을 건너뜁니다${NC}"
    echo "나중에 다음 명령어로 발급할 수 있습니다:"
    echo "  sudo certbot --nginx -d $DOMAIN_NAME"
fi

# 11. 최종 확인
echo ""
echo -e "${GREEN}✅ HTTPS 설정 완료!${NC}"
echo ""
echo -e "${BLUE}📋 다음 단계:${NC}"
echo "1. Vercel 환경 변수 업데이트:"
echo "   NEXT_PUBLIC_BACKEND_URL=https://$DOMAIN_NAME"
echo ""
echo "2. 백엔드 테스트:"
if [ "$ISSUE_SSL" = "y" ] || [ "$ISSUE_SSL" = "Y" ]; then
    echo "   https://$DOMAIN_NAME/health"
    echo "   https://$DOMAIN_NAME/docs"
else
    echo "   http://$DOMAIN_NAME/health"
    echo "   http://$DOMAIN_NAME/docs"
    echo "   (SSL 인증서 발급 후 https:// 사용 가능)"
fi
echo ""
echo "3. SSL 인증서 자동 갱신 설정:"
echo "   sudo certbot renew --dry-run"
echo ""

