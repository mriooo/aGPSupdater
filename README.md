# Weekly File Telegram Bot

A Docker-based Telegram bot that automatically sends files every Sunday using the [huami-token](https://github.com/argrento/huami-token) project to generate Amazfit/Zepp device token information. Perfect for use with [Gadgetbridge](https://gadgetbridge.org/) to update ZEPP OS and Xiaomi Smart Band AGPS firmware.

## Features

- 🤖 Automated weekly file sending (every Sunday at 10:00 AM)
- 📱 Integration with huami-token for device token generation
- � Perfect for Gadgetbridge - ZEPP OS and Xiaomi Smart Band AGPS firmware updates
- � Full Docker containerization
- ⚙️ Easy configuration via environment variables
- 📊 Bot commands for status and manual sending
- 🔄 Automatic retry and error handling

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- Telegram Bot Token (get from [@BotFather](https://t.me/BotFather))
- Your Telegram Chat ID
- Amazfit/Zepp account credentials

### 2. Configuration

1. Copy the environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
AUTHORIZED_USERS=123456789,987654321
HUAMI_EMAIL=your_amazfit_email@example.com
HUAMI_PASSWORD=your_amazfit_password
```

**Authorization Configuration:**
- `AUTHORIZED_USERS`: Comma-separated list of Telegram user IDs who can use the bot
- Leave empty to allow everyone (not recommended for security)
- To get your user ID, send a message to [@userinfobot](https://t.me/userinfobot)

### 3. Get Your Telegram Chat ID

Send a message to your bot, then visit:
```
https://api.telegram.org/bot<TOKEN>/getUpdates
```
Look for `chat_id` in the response.

### 4. Run the Bot

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the bot
docker-compose down
```

## Bot Commands

- `/start` - Start the bot and see available commands
- `/status` - Check bot status and next scheduled send
- `/send_now` - Generate and send file immediately
- `/next_send` - Show time until next automatic send

**Note:** All commands require authorization. If `AUTHORIZED_USERS` is configured, only those users can interact with the bot.

## How It Works

1. **Weekly Schedule**: The bot runs a background scheduler that triggers every Sunday at 10:00 AM
2. **Token Generation**: Uses the huami-token script to authenticate with Amazfit/Zepp servers and retrieve device tokens
3. **File Creation**: Creates a formatted text file with the token information
4. **Telegram Delivery**: Sends the generated file as a document to your configured chat

## File Output

The bot generates files in the format:
```
huami_token_YYYYMMDD_HHMMSS.txt
```

With content including:
- Device MAC address
- Bluetooth authentication key
- Device active status
- Generation timestamp

## Directory Structure

```
.
├── bot.py              # Main bot application
├── Dockerfile          # Container configuration
├── docker-compose.yml  # Compose configuration
├── requirements.txt    # Python dependencies
├── .env.example       # Environment template
└── README.md          # This file
```

## Development

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Clone huami-token:
```bash
git clone https://github.com/argrento/huami-token.git
cd huami-token
pip install -e ".[dev]"
cd ..
```

**Alternative: Huafetcher**
For more advanced features, you can also use [huami-token](https://github.com/argrento/huami-token):
```bash
git clone https://github.com/argrento/huami-token
```

3. Set environment variables and run:
```bash
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export AUTHORIZED_USERS="123456789,987654321"
export HUAMI_EMAIL="your_email"
export HUAMI_PASSWORD="your_password"
python bot.py
```

### Building the Docker Image

```bash
# Build the image
docker build -t weekly-file-bot .

# Run with environment variables
docker run -d \
  --name weekly-file-bot \
  -e TELEGRAM_BOT_TOKEN="your_token" \
  -e TELEGRAM_CHAT_ID="your_chat_id" \
  -e AUTHORIZED_USERS="123456789,987654321" \
  -e HUAMI_EMAIL="your_email" \
  -e HUAMI_PASSWORD="your_password" \
  weekly-file-bot
```

## Troubleshooting

### Common Issues

1. **Bot doesn't respond**: Check if the bot token is correct and the bot is running
2. **No file generated**: Verify Amazfit credentials and ensure your device is paired in the Zepp app
3. **Unauthorized access**: Ensure your user ID is in the `AUTHORIZED_USERS` list, or leave it empty for open access
4. **Permission errors**: Ensure the Docker container has proper permissions

### Logs

View detailed logs:
```bash
docker-compose logs weekly-file-bot
```

**Note:** The bot uses Python's standard logging to stdout/stderr. Logs are managed by Docker and can be viewed with `docker-compose logs`. No separate log directory is needed.

### Health Checks

The container includes a health check that runs every 30 seconds. Check container health:
```bash
docker ps
```

## Security Notes

- Store your `.env` file securely and never commit it to version control
- The bot runs as a non-root user inside the container
- Consider using Docker secrets for production deployments

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Use with Gadgetbridge

This bot is perfect for Gadgetbridge users who need to:
- Update ZEPP OS firmware on Amazfit/Zepp devices
- Update AGPS firmware for Xiaomi Smart Band devices
- Maintain regular backup of device authentication keys

**Gadgetbridge Repository**: [https://github.com/Gadgetbridge/gadgetbridge](https://github.com/Gadgetbridge/gadgetbridge)

**Related Projects**:
- [huami-token](https://github.com/argrento/huami-token) - Token generation for Amazfit/Zepp devices
- [huafetcher](https://github.com/Hypfer/huafetcher) - Advanced Huami device data fetcher
- [Gadgetbridge](https://github.com/Gadgetbridge/gadgetbridge) - Android companion for wearables

## Support

If you encounter issues:
1. Check the logs for error messages
2. Verify your environment variables
3. Ensure your Amazfit account credentials are correct
4. Make sure your device is properly paired in the Zepp app
