#!/bin/bash

# Coffee Order Server Installation Script for Raspberry Pi
# Run this script as: bash install.sh

set -e

echo "🍵 Installing Coffee Order Notification Server..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please run this script as a regular user (not root)${NC}"
    echo "Usage: bash install.sh"
    exit 1
fi

# Get the current username
CURRENT_USER=$(whoami)
echo -e "${YELLOW}Installing for user: $CURRENT_USER${NC}"

# Create directory structure
SERVER_DIR="/home/$CURRENT_USER/order-server"
echo -e "${YELLOW}Creating directory: $SERVER_DIR${NC}"
mkdir -p "$SERVER_DIR"
mkdir -p "/home/$CURRENT_USER/scripts"

# Update system packages
echo -e "${YELLOW}Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

# Install Python and pip if not already installed
echo -e "${YELLOW}Installing Python3 and pip...${NC}"
sudo apt install -y python3 python3-pip python3-venv

# Create virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
cd "$SERVER_DIR"
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install Flask==2.3.3 requests==2.31.0

# Copy files to the server directory
echo -e "${YELLOW}Setting up server files...${NC}"
cp order_server.py "$SERVER_DIR/"
cp requirements.txt "$SERVER_DIR/"

# Make server executable
chmod +x "$SERVER_DIR/order_server.py"

# Create log directory
sudo mkdir -p /var/log
sudo touch /var/log/order_server.log
sudo chown $CURRENT_USER:$CURRENT_USER /var/log/order_server.log

# Update service file with correct username
echo -e "${YELLOW}Updating service file for user: $CURRENT_USER${NC}"
sed -i "s/User=carousel/User=$CURRENT_USER/g" order-server.service
sed -i "s/Group=carousel/Group=$CURRENT_USER/g" order-server.service
sed -i "s|/home/carousel|/home/$CURRENT_USER|g" order-server.service

# Install systemd service
echo -e "${YELLOW}Installing systemd service...${NC}"
sudo cp order-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable order-server
sudo systemctl start order-server

# Create example LED flash script
echo -e "${YELLOW}Creating example LED flash script...${NC}"
cat > /home/$CURRENT_USER/scripts/flash_led.py << 'EOF'
#!/usr/bin/env python3
import time
import os

# Simple LED flash using built-in LED (if available)
def flash_led():
    led_path = "/sys/class/leds/led0/brightness"
    if os.path.exists(led_path):
        try:
            # Flash 3 times
            for _ in range(3):
                with open(led_path, 'w') as f:
                    f.write('1')
                time.sleep(0.5)
                with open(led_path, 'w') as f:
                    f.write('0')
                time.sleep(0.5)
        except PermissionError:
            print("LED control requires root permissions")
    else:
        print("LED control not available on this system")

if __name__ == "__main__":
    flash_led()
EOF

chmod +x /home/$CURRENT_USER/scripts/flash_led.py

# Generate secure API key
API_KEY=$(openssl rand -hex 32)
echo -e "${YELLOW}Generated secure API key: ${GREEN}$API_KEY${NC}"

# Update API key in server file
sed -i "s/your-secure-api-key-here/$API_KEY/g" "$SERVER_DIR/order_server.py"

# Check firewall and open port (if ufw is enabled)
if command -v ufw &> /dev/null; then
    if sudo ufw status | grep -q "Status: active"; then
        echo -e "${YELLOW}Opening port 3000 in firewall...${NC}"
        sudo ufw allow 3000/tcp
    fi
fi

# Get IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}✅ Installation completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Update Firebase Cloud Function with:"
echo "   - Raspberry Pi IP: http://$IP_ADDRESS:3000"
echo "   - API Key: $API_KEY"
echo ""
echo "2. Check service status:"
echo "   sudo systemctl status order-server"
echo ""
echo "3. View logs:"
echo "   sudo journalctl -u order-server -f"
echo "   or"
echo "   tail -f /var/log/order_server.log"
echo ""
echo "4. Test the server:"
echo "   curl http://$IP_ADDRESS:3000/health"
echo ""
echo -e "${YELLOW}🔧 Configuration Files:${NC}"
echo "- Server: $SERVER_DIR/order_server.py"
echo "- Service: /etc/systemd/system/order-server.service"
echo "- Log: /var/log/order_server.log"
echo ""
echo -e "${YELLOW}⚠️  Security Notes:${NC}"
echo "- API key is stored in: $SERVER_DIR/order_server.py"
echo "- Keep this key secure and use the same key in Firebase"
echo "- Consider setting up port forwarding on your router for external access"
echo "- For internet access, you may want to use ngrok or similar service" 