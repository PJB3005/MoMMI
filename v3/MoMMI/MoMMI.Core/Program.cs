using System.Threading.Tasks;
using MoMMI.Core.Logging;

namespace MoMMI.Core
{
    internal static class Program
    {
        private static void Main(string[] args)
        {
            var logging = new LogManager();
            SetupLogging(logging);

            logging.RootSawmill.Info("Beep boop");

            var config = new ConfigManager(logging.GetSawmill("config"), "./config");
            config.LoadConfig();

            new Master(config, logging).Run();
        }

        private static void SetupLogging(ILogManager logManager)
        {
            var root = logManager.RootSawmill;
            root.AddHandler(new ConsoleLogHandler());
        }
    }
}
