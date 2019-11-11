using System;
using Discord;
using MoMMI.Core.Logging;

namespace MoMMI.Core.Utility
{
    internal static class LogExt
    {
        public static LogLevel Convert(this Discord.LogSeverity severity)
        {
            switch (severity)
            {
                case LogSeverity.Critical:
                    return LogLevel.Fatal;

                case LogSeverity.Error:
                    return LogLevel.Error;

                case LogSeverity.Warning:
                    return LogLevel.Warning;

                case LogSeverity.Info:
                    return LogLevel.Info;

                case LogSeverity.Verbose:
                case LogSeverity.Debug:
                    return LogLevel.Debug;

                default:
                    throw new ArgumentOutOfRangeException(nameof(severity), severity, null);
            }
        }
    }
}
