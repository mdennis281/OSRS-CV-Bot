from bots.master_mixer import BotConfig, BotExecutor


def main():
    config = BotConfig()
    bot = BotExecutor(config)
    
    bot.start()
    
main()