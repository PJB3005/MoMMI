using System;
using JetBrains.Annotations;

namespace MoMMI.Core
{
    [UsedImplicitly]
    public abstract class Module
    {
        protected IMaster Master { get; private set; }

        internal void Initialize(IMaster master)
        {

        }
    }
}
