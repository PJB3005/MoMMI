using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using MoMMI.Core.Logging;

namespace MoMMI.Core
{
    internal sealed class ModuleManager : IModuleManager
    {
        private readonly IMaster _master;
        private readonly ISawmill _sawmill;
        private const string ModulePath = "MoMMI.Modules/bin/Debug/netcoreapp3.0/MoMMI.Modules.dll";

        private AssemblyLoadContext _moduleLoadContext;

        public IReadOnlyList<Module> Modules => _modules;
        private readonly List<Module> _modules = new List<Module>();

        public ModuleManager(IMaster master, ISawmill sawmill)
        {
            _master = master;
            _sawmill = sawmill;
        }

        public void ReloadModules()
        {
            _sawmill.Info("Reloading modules!");
            // TODO: Maybe ensure no modules are running while reloading to prevent race conditions.

            if (_moduleLoadContext != null)
            {
                _sawmill.Debug("Unloading previous modules!");
                _modules.Clear();
                _moduleLoadContext.Unload();
                _moduleLoadContext = null;
            }

            _moduleLoadContext = new AssemblyLoadContext("MoMMI Modules", true);

            Assembly assembly;
            using (var file = File.OpenRead(ModulePath))
            {
                assembly = _moduleLoadContext.LoadFromStream(file);

                foreach (var moduleType in assembly.GetTypes().Where(t => t.BaseType == typeof(Module)))
                {
                    _sawmill.Debug("Found module {0}", moduleType);
                    var module = (Module) Activator.CreateInstance(moduleType);
                    _modules.Add(module);
                    module.Initialize(_master);
                }
            }
        }
    }

    public interface IModuleManager
    {
        void ReloadModules();
        IReadOnlyList<Module> Modules { get; }
    }
}
