using System;

namespace MoMMI.Core.Logging
{
    /// <summary>
    ///     Log handler that prints to console.
    /// </summary>
    public sealed class ConsoleLogHandler : ILogHandler
    {
        private readonly object locker = new object();

        public void Log(in LogMessage message)
        {
            var name = LogMessage.LogLevelToName(message.Level);
            var color = LogLevelToConsoleColor(message.Level);

            lock (locker)
            {
                Console.Write('[');
                Console.ForegroundColor = color;
                Console.Write(name);
                Console.ResetColor();
                Console.WriteLine("] {0}: {1}", message.SawmillName, message.Message);
            }
        }

        private static ConsoleColor LogLevelToConsoleColor(LogLevel level)
        {
            switch (level)
            {
                case LogLevel.Debug:
                    return ConsoleColor.DarkBlue;

                case LogLevel.Info:
                    return ConsoleColor.Cyan;

                case LogLevel.Warning:
                    return ConsoleColor.Yellow;

                case LogLevel.Error:
                case LogLevel.Fatal:
                    return ConsoleColor.Red;

                default:
                    return ConsoleColor.White;
            }
        }
    }
}
