from bots.woodcutter import BotConfig, BotExecutor


def main():
    config = BotConfig()
    bot = BotExecutor(config)
    
    bot.start()
    
main()