using System;
using System.Threading.Tasks;
using Discord;
using MoMMI.Core;

namespace MoMMI.Modules
{
    public sealed class Ping : Module
    {
        [Command("ping")]
        public async Task Pong(IMessageChannel channel)
        {
            await channel.SendMessageAsync("Pong");
        }
    }
}
