using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;

internal static class Program
{
    private static readonly string SimioDir = @"D:\Program Files\Simio LLC\Simio";

    private static int Main(string[] args)
    {
        var modelPath = GetArg(args, "--source") ?? GetArg(args, "--model");
        var outputPath = GetArg(args, "--output");
        var mode = GetArg(args, "--mode") ?? "run-plan";
        var tempDir = GetArg(args, "--temp") ?? Path.Combine(Directory.GetCurrentDirectory(), ".tmp", "simio-temp");
        var startedAt = DateTimeOffset.UtcNow;
        var result = new Dictionary<string, object?>
        {
            ["Status"] = "Failed",
            ["RunnerBackend"] = "local",
            ["Mode"] = mode,
            ["StartedAt"] = startedAt.ToString("O"),
            ["ModelPath"] = modelPath,
            ["SourceTemplatePath"] = modelPath,
            ["ResultModelPath"] = outputPath,
            ["SimioDir"] = SimioDir,
            ["TempDir"] = tempDir,
        };

        try
        {
            if (string.IsNullOrWhiteSpace(modelPath) || !File.Exists(modelPath))
            {
                throw new FileNotFoundException("Generated Simio model package was not found.", modelPath);
            }
            if (!string.IsNullOrWhiteSpace(outputPath))
            {
                var outputDir = Path.GetDirectoryName(Path.GetFullPath(outputPath));
                if (!string.IsNullOrWhiteSpace(outputDir))
                {
                    Directory.CreateDirectory(outputDir);
                }
            }
            Directory.CreateDirectory(tempDir);
            Environment.SetEnvironmentVariable("TEMP", tempDir);
            Environment.SetEnvironmentVariable("TMP", tempDir);
            ConfigureAssemblyResolution();
            var simioApi = AssemblyLoadContext.Default.LoadFromAssemblyPath(Path.Combine(SimioDir, "SimioAPI.dll"));
            var simio = AssemblyLoadContext.Default.LoadFromAssemblyPath(Path.Combine(SimioDir, "Simio.dll"));
            var simioDllPath = Path.Combine(SimioDir, "SimioDLL.dll");
            var simioDll = File.Exists(simioDllPath)
                ? AssemblyLoadContext.Default.LoadFromAssemblyPath(simioDllPath)
                : null;
            result["LoadedAssemblies"] = new[] { simioApi.FullName, simio.FullName };

            if (mode.Equals("probe", StringComparison.OrdinalIgnoreCase))
            {
                result["Status"] = "ProbeSucceeded";
                result["CandidateTypes"] = AppDomain.CurrentDomain
                    .GetAssemblies()
                    .SelectMany(SafeGetTypes)
                    .Where(t => t.FullName != null && (
                        t.FullName.Contains("Project", StringComparison.OrdinalIgnoreCase)
                        || t.FullName.Contains("Factory", StringComparison.OrdinalIgnoreCase)
                        || t.FullName.Contains("File", StringComparison.OrdinalIgnoreCase)))
                    .Select(t => t.FullName)
                    .Distinct()
                    .OrderBy(name => name)
                    .Take(250)
                    .ToArray();
                result["CandidateMethods"] = AppDomain.CurrentDomain
                    .GetAssemblies()
                    .SelectMany(SafeGetTypes)
                    .SelectMany(t => t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance)
                        .Where(m => m.Name.Contains("Load", StringComparison.OrdinalIgnoreCase)
                            || m.Name.Contains("Open", StringComparison.OrdinalIgnoreCase)
                            || m.Name.Contains("Project", StringComparison.OrdinalIgnoreCase))
                        .Select(m => $"{t.FullName}.{m}"))
                    .Distinct()
                    .Take(250)
                    .ToArray();
                WriteJson(result);
                return 0;
            }

            if (mode.Equals("stats-probe", StringComparison.OrdinalIgnoreCase))
            {
                result["Status"] = "ProbeSucceeded";
                result["InteractiveStatistics"] = TryReadInteractiveStatistics(modelPath);
                WriteJson(result);
                return 0;
            }

            var factoryType = FindType("SimioProjectFactory");
            result["FactoryType"] = factoryType.FullName;
            if (mode.Equals("factory-probe", StringComparison.OrdinalIgnoreCase))
            {
                result["Status"] = "ProbeSucceeded";
                result["FactoryMethods"] = factoryType
                    .GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance)
                    .Select(m => m.ToString())
                    .Take(50)
                    .ToArray();
                WriteJson(result);
                return 0;
            }

            var project = LoadProject(factoryType, modelPath);
            result["ProjectType"] = project.GetType().FullName;
            result["ProjectName"] = GetProperty(project, "Name")?.ToString();
            result["GeneratedModelPath"] = modelPath;

            var selection = SelectModel(project);
            result["AvailableModels"] = selection.Candidates;
            result["SelectedModelReason"] = selection.Reason;
            var model = selection.Model;
            result["ModelType"] = model.GetType().FullName;
            result["ModelName"] = GetProperty(model, "Name")?.ToString();

            var plan = GetProperty(model, "Plan");
            if (plan == null)
            {
                throw new InvalidOperationException("The Simio model does not expose a Plan object.");
            }
            result["PlanType"] = plan.GetType().FullName;

            if (mode.Equals("loaded-probe", StringComparison.OrdinalIgnoreCase))
            {
                result["Status"] = "ProbeSucceeded";
                result["ProjectMembers"] = DescribeType(project.GetType());
                result["ModelMembers"] = DescribeType(model.GetType());
                result["PlanMembers"] = DescribeType(plan.GetType());
                result["PlanLogMembers"] = plan.GetType()
                    .GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                    .Where(p => p.Name.Contains("Log", StringComparison.OrdinalIgnoreCase)
                        || p.Name.Contains("Result", StringComparison.OrdinalIgnoreCase))
                    .Select(p =>
                    {
                        object? value = null;
                        try
                        {
                            value = p.GetValue(plan);
                        }
                        catch
                        {
                            // Probe mode should not fail merely because a log property is lazy.
                        }
                        return new
                        {
                            Property = p.Name,
                            DeclaredType = p.PropertyType.FullName,
                            RuntimeType = value?.GetType().FullName,
                            Members = value == null ? null : DescribeType(value.GetType()),
                        };
                    })
                    .ToArray();
                result["ResultCandidateTypes"] = AppDomain.CurrentDomain
                    .GetAssemblies()
                    .SelectMany(SafeGetTypes)
                    .Where(t => t.FullName != null && (
                        t.FullName.Contains("Result", StringComparison.OrdinalIgnoreCase)
                        || t.FullName.Contains("Statistic", StringComparison.OrdinalIgnoreCase)
                        || t.FullName.Contains("Dashboard", StringComparison.OrdinalIgnoreCase)
                        || t.FullName.Contains("Report", StringComparison.OrdinalIgnoreCase)))
                    .Select(t => new
                    {
                        Type = t.FullName,
                        Members = DescribeType(t),
                    })
                    .Take(80)
                    .ToArray();
                WriteJson(result);
                return 0;
            }

            if (mode.Equals("export-probe", StringComparison.OrdinalIgnoreCase))
            {
                result["Status"] = "ProbeSucceeded";
                result["LogExports"] = plan.GetType()
                    .GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                    .Where(p => p.Name.Contains("Log", StringComparison.OrdinalIgnoreCase)
                        || p.Name.Contains("Result", StringComparison.OrdinalIgnoreCase))
                    .Select(p => ProbeLogExport(plan, p))
                    .ToArray();
                WriteJson(result);
                return 0;
            }

            InvokeRunPlan(plan);
            result["PostRunLogExports"] = plan.GetType()
                .GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                .Where(p => p.Name.Contains("Log", StringComparison.OrdinalIgnoreCase)
                    || p.Name.Contains("Result", StringComparison.OrdinalIgnoreCase))
                .Select(p => ProbeLogExport(plan, p))
                .ToArray();
            result["PostRunMetrics"] = BuildPostRunMetrics(plan);
            if (!string.IsNullOrWhiteSpace(outputPath))
            {
                SaveProject(factoryType, project, outputPath);
                result["ResultModelPath"] = outputPath;
                result["ResultModelSaved"] = File.Exists(outputPath);
                result["InteractiveStatistics"] = TryReadInteractiveStatistics(outputPath);
            }
            result["Status"] = "Completed";
            result["PlanRunCompleted"] = true;
            result["Message"] = "Simio Plan.RunPlan completed.";
            result["CompletedAt"] = DateTimeOffset.UtcNow.ToString("O");
            WriteJson(result);
            return 0;
        }
        catch (TargetInvocationException error)
        {
            WriteError(result, error.InnerException ?? error);
            return 2;
        }
        catch (Exception error)
        {
            WriteError(result, error);
            return 1;
        }
    }

    private static void ConfigureAssemblyResolution()
    {
        AssemblyLoadContext.Default.Resolving += (context, name) =>
        {
            var candidate = Path.Combine(SimioDir, name.Name + ".dll");
            return File.Exists(candidate) ? context.LoadFromAssemblyPath(candidate) : null;
        };
    }

    private static Type FindType(string typeName)
    {
        var type = AppDomain.CurrentDomain
            .GetAssemblies()
            .SelectMany(SafeGetTypes)
            .FirstOrDefault(t => t.Name.Equals(typeName, StringComparison.Ordinal));
        if (type == null)
        {
            throw new InvalidOperationException($"Unable to find Simio type {typeName}.");
        }
        return type;
    }

    private static object LoadProject(Type factoryType, string modelPath)
    {
        var methodNames = new[] { "LoadProject", "LoadFromFile", "OpenProject", "Open" };
        foreach (var method in factoryType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance))
        {
            if (!methodNames.Contains(method.Name))
            {
                continue;
            }
            var parameters = method.GetParameters();
            if (parameters.Length == 1 && parameters[0].ParameterType == typeof(string))
            {
                var target = method.IsStatic ? null : Activator.CreateInstance(factoryType);
                var project = method.Invoke(target, new object[] { modelPath });
                if (project != null)
                {
                    return project;
                }
            }
        }
        throw new MissingMethodException(factoryType.FullName, "LoadProject/LoadFromFile/OpenProject/Open(string)");
    }

    private static void SaveProject(Type factoryType, object project, string outputPath)
    {
        foreach (var method in factoryType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance))
        {
            if (method.Name != "SaveProject" && method.Name != "Save" && method.Name != "SaveAs")
            {
                continue;
            }
            var parameters = method.GetParameters();
            var target = method.IsStatic ? null : Activator.CreateInstance(factoryType);
            if (parameters.Length == 2
                && parameters[0].ParameterType.IsInstanceOfType(project)
                && parameters[1].ParameterType == typeof(string))
            {
                method.Invoke(target, new object[] { project, outputPath });
                return;
            }
            if (parameters.Length == 3
                && parameters[0].ParameterType.IsInstanceOfType(project)
                && parameters[1].ParameterType == typeof(string)
                && parameters[2].ParameterType.IsByRef)
            {
                var values = new object?[] { project, outputPath, null };
                method.Invoke(target, values);
                return;
            }
            if (parameters.Length == 1 && parameters[0].ParameterType == typeof(string))
            {
                method.Invoke(project, new object[] { outputPath });
                return;
            }
        }
        throw new MissingMethodException(factoryType.FullName, "SaveProject/Save/SaveAs");
    }

    private sealed record ModelSelection(object Model, object[] Candidates, string Reason);

    private static ModelSelection SelectModel(object project)
    {
        var models = GetProperty(project, "Models");
        if (models == null)
        {
            throw new InvalidOperationException("The Simio project does not expose Models.");
        }
        var items = new List<object>();
        if (models is IEnumerable enumerable)
        {
            foreach (var item in enumerable)
            {
                if (item != null)
                {
                    items.Add(item);
                }
            }
        }
        if (items.Count == 0)
        {
            var indexer = models.GetType()
                .GetProperties()
                .FirstOrDefault(p => p.GetIndexParameters().Length == 1 && p.GetIndexParameters()[0].ParameterType == typeof(int));
            if (indexer != null)
            {
                var count = GetProperty(models, "Count");
                var max = count is int intCount ? intCount : 8;
                for (var index = 0; index < max; index++)
                {
                    try
                    {
                        var item = indexer.GetValue(models, new object[] { index });
                        if (item != null)
                        {
                            items.Add(item);
                        }
                    }
                    catch
                    {
                        break;
                    }
                }
            }
        }
        if (items.Count == 0)
        {
            throw new InvalidOperationException("No model was found in the Simio project.");
        }
        var candidates = items
            .Select((item, index) => new
            {
                Index = index,
                Name = GetProperty(item, "Name")?.ToString(),
                Type = item.GetType().FullName,
                HasPlan = GetProperty(item, "Plan") != null,
                HasRunSetup = GetProperty(item, "RunSetup") != null,
                ResourceLogic = GetProperty(item, "ResourceLogic")?.ToString(),
            })
            .ToArray();
        var exactModel = items.FirstOrDefault(item =>
            string.Equals(GetProperty(item, "Name")?.ToString(), "Model", StringComparison.OrdinalIgnoreCase));
        if (exactModel != null)
        {
            return new ModelSelection(exactModel, candidates, "Selected model named 'Model'.");
        }
        var nonEntityModel = items.FirstOrDefault(item =>
        {
            var name = GetProperty(item, "Name")?.ToString();
            return !string.Equals(name, "ModelEntity", StringComparison.OrdinalIgnoreCase)
                && GetProperty(item, "Plan") != null;
        });
        if (nonEntityModel != null)
        {
            return new ModelSelection(nonEntityModel, candidates, "Selected first non-ModelEntity model with a Plan.");
        }
        return new ModelSelection(items[0], candidates, "Fell back to first model.");
    }

    private static void InvokeRunPlan(object plan)
    {
        var runPlanOptionsType = AppDomain.CurrentDomain
            .GetAssemblies()
            .SelectMany(SafeGetTypes)
            .FirstOrDefault(t => t.FullName == "SimioAPI.RunPlanOptions");
        var runPlanWithOptions = plan.GetType()
            .GetMethods()
            .FirstOrDefault(m => m.Name == "RunPlan" && m.GetParameters().Length == 1);
        if (runPlanOptionsType != null && runPlanWithOptions != null)
        {
            var options = Activator.CreateInstance(runPlanOptionsType);
            runPlanOptionsType.GetProperty("AllowDesignErrors")?.SetValue(options, true);
            runPlanWithOptions.Invoke(plan, new[] { options });
            return;
        }
        var runPlan = plan.GetType()
            .GetMethods()
            .FirstOrDefault(m => m.Name == "RunPlan" && m.GetParameters().Length == 0);
        if (runPlan == null)
        {
            throw new MissingMethodException(plan.GetType().FullName, "RunPlan");
        }
        runPlan.Invoke(plan, Array.Empty<object>());
    }

    private static object? GetProperty(object target, string propertyName)
    {
        var property = target.GetType().GetProperty(propertyName);
        if (property != null)
        {
            return property.GetValue(target);
        }
        foreach (var interfaceType in target.GetType().GetInterfaces())
        {
            property = interfaceType.GetProperty(propertyName);
            if (property != null)
            {
                return property.GetValue(target);
            }
        }
        return null;
    }

    private static IEnumerable<Type> SafeGetTypes(Assembly assembly)
    {
        try
        {
            return assembly.GetTypes();
        }
        catch (ReflectionTypeLoadException error)
        {
            return error.Types.Where(t => t != null)!;
        }
    }

    private static object DescribeType(Type type)
    {
        return new
        {
            Type = type.FullName,
            Properties = type
                .GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static)
                .Select(p => $"{p.PropertyType.FullName} {p.Name}")
                .Distinct()
                .Take(120)
                .ToArray(),
            Methods = type
                .GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static)
                .Where(m => !m.IsSpecialName)
                .Select(m => m.ToString())
                .Distinct()
                .Take(120)
                .ToArray(),
        };
    }

    private static object ProbeLogExport(object plan, PropertyInfo property)
    {
        object? log = null;
        try
        {
            log = property.GetValue(plan);
        }
        catch (Exception error)
        {
            return new
            {
                Property = property.Name,
                Error = error.Message,
            };
        }
        if (log == null)
        {
            return new { Property = property.Name, Status = "Null" };
        }
        return new
        {
            Property = property.Name,
            RuntimeType = log.GetType().FullName,
            Count = GetProperty(log, "Count"),
            Samples = SampleEnumerable(log, 5),
            Interactive = ProbeExportMethod(log, "ExportForInteractive"),
            Plan = ProbeExportMethod(log, "ExportForPlan"),
        };
    }

    private static object SampleEnumerable(object value, int limit)
    {
        if (value is not IEnumerable enumerable || value is string)
        {
            return new { Status = "NotEnumerable" };
        }
        var items = new List<object?>();
        var count = 0;
        try
        {
            foreach (var item in enumerable)
            {
                if (count >= limit)
                {
                    break;
                }
                items.Add(DescribeObject(item, 0));
                count++;
            }
        }
        catch (Exception error)
        {
            return new
            {
                Status = "Failed",
                ExceptionType = error.GetType().FullName,
                Message = error.Message,
            };
        }
        return new
        {
            Status = "Sampled",
            Count = count,
            Items = items,
        };
    }

    private static object BuildPostRunMetrics(object plan)
    {
        var stateRows = EnumerateLog(plan, "ResourceStateLog").ToArray();
        var capacityRows = EnumerateLog(plan, "ResourceCapacityLog").ToArray();
        var horizonHours = InferRunHorizonHours(plan);
        var resourceNames = stateRows
            .Select(row => GetString(row, "ResourceName") ?? GetString(row, "ResourceId"))
            .Concat(capacityRows.Select(row => GetString(row, "ResourceName") ?? GetString(row, "ResourceId")))
            .Where(name => !string.IsNullOrWhiteSpace(name))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(name => name)
            .ToArray();

        var resources = resourceNames
            .Select(resource =>
            {
                var scopedStates = stateRows
                    .Where(row => string.Equals(
                        GetString(row, "ResourceName") ?? GetString(row, "ResourceId"),
                        resource,
                        StringComparison.OrdinalIgnoreCase))
                    .ToArray();
                var scopedCapacity = capacityRows
                    .Where(row => string.Equals(
                        GetString(row, "ResourceName") ?? GetString(row, "ResourceId"),
                        resource,
                        StringComparison.OrdinalIgnoreCase))
                    .ToArray();
                var stateMinutes = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase);
                foreach (var row in scopedStates)
                {
                    var state = GetString(row, "StateName") ?? GetString(row, "AutoStateName") ?? "Unknown";
                    var minutes = DurationMinutes(row, horizonHours);
                    stateMinutes[state] = stateMinutes.TryGetValue(state, out var existing)
                        ? existing + minutes
                        : minutes;
                }
                var scheduledCapacityMinutes = 0.0;
                var utilizedCapacityMinutes = 0.0;
                foreach (var row in scopedCapacity)
                {
                    var minutes = DurationMinutes(row, horizonHours);
                    scheduledCapacityMinutes += minutes * (GetDouble(row, "CapacityScheduled") ?? 0.0);
                    utilizedCapacityMinutes += minutes * (GetDouble(row, "CapacityUtilized") ?? 0.0);
                }
                var busyMinutes = StateMinutes(stateMinutes, "Processing", "Busy", "Utilized");
                var starvedMinutes = StateMinutes(stateMinutes, "Starved");
                var blockedMinutes = StateMinutes(stateMinutes, "Blocked");
                var observedMinutes = stateMinutes.Values.Sum();
                var utilizationPercent = scheduledCapacityMinutes > 0
                    ? Math.Round(utilizedCapacityMinutes / scheduledCapacityMinutes * 100.0, 4)
                    : (observedMinutes > 0 ? Math.Round(busyMinutes / observedMinutes * 100.0, 4) : (double?)null);
                return new
                {
                    ResourceID = resource,
                    UtilizationPercent = utilizationPercent,
                    BusyMinutes = Math.Round(busyMinutes, 4),
                    StarvedMinutes = Math.Round(starvedMinutes, 4),
                    BlockedMinutes = Math.Round(blockedMinutes, 4),
                    ObservedMinutes = Math.Round(observedMinutes, 4),
                    ScheduledCapacityMinutes = Math.Round(scheduledCapacityMinutes, 4),
                    UtilizedCapacityMinutes = Math.Round(utilizedCapacityMinutes, 4),
                    StateMinutes = stateMinutes
                        .OrderBy(item => item.Key)
                        .ToDictionary(item => item.Key, item => Math.Round(item.Value, 4)),
                };
            })
            .ToArray();

        return new
        {
            Status = resources.Length > 0 ? "Parsed" : "Unavailable",
            HorizonHours = horizonHours,
            ResourceStateRowCount = stateRows.Length,
            ResourceCapacityRowCount = capacityRows.Length,
            ResourceUtilization = new
            {
                Status = resources.Length > 0 ? "ParsedFromPostRunLogs" : "Unavailable",
                Resources = resources,
                SourceLogs = new[] { "ResourceStateLog", "ResourceCapacityLog" },
            },
            QueueMetrics = new
            {
                Status = "Unavailable",
                Message = "No queue length or waiting-time post-run log has been mapped yet.",
            },
            WipMetrics = new
            {
                Status = "Unavailable",
                Message = "No system WIP post-run log has been mapped yet.",
            },
        };
    }

    private static double? InferRunHorizonHours(object plan)
    {
        var candidates = EnumerateLog(plan, "StateObservationLog")
            .Select(row => GetDouble(row, "EndTimeOffset"))
            .Where(value => value.HasValue && value.Value > 0 && value.Value < 100000)
            .Select(value => value!.Value)
            .ToArray();
        if (candidates.Length > 0)
        {
            return candidates.Max();
        }
        return null;
    }

    private static IEnumerable<object> EnumerateLog(object plan, string propertyName)
    {
        var log = GetProperty(plan, propertyName);
        if (log is not IEnumerable enumerable || log is string)
        {
            return Array.Empty<object>();
        }
        var rows = new List<object>();
        foreach (var item in enumerable)
        {
            if (item != null)
            {
                rows.Add(item);
            }
        }
        return rows;
    }

    private static double DurationMinutes(object row, double? horizonHours)
    {
        var start = GetDouble(row, "StartTimeOffset");
        var end = GetDouble(row, "EndTimeOffset");
        if (start.HasValue && end.HasValue && end.Value >= start.Value)
        {
            var cappedEnd = horizonHours.HasValue ? Math.Min(end.Value, horizonHours.Value) : end.Value;
            var cappedStart = horizonHours.HasValue ? Math.Min(start.Value, horizonHours.Value) : start.Value;
            if (cappedEnd < cappedStart)
            {
                return 0.0;
            }
            return (cappedEnd - cappedStart) * 60.0;
        }
        return 0.0;
    }

    private static double StateMinutes(Dictionary<string, double> stateMinutes, params string[] stateNames)
    {
        return stateNames.Sum(name =>
            stateMinutes.TryGetValue(name, out var minutes) ? minutes : 0.0);
    }

    private static string? GetString(object target, string propertyName)
    {
        return GetProperty(target, propertyName)?.ToString();
    }

    private static double? GetDouble(object target, string propertyName)
    {
        var value = GetProperty(target, propertyName);
        if (value == null)
        {
            return null;
        }
        if (value is double doubleValue)
        {
            return doubleValue;
        }
        if (value is float floatValue)
        {
            return floatValue;
        }
        if (value is int intValue)
        {
            return intValue;
        }
        if (double.TryParse(value.ToString(), out var parsed))
        {
            return parsed;
        }
        return null;
    }

    private static object ProbeExportMethod(object log, string methodName)
    {
        var method = log.GetType()
            .GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
            .FirstOrDefault(m => m.Name == methodName && m.GetParameters().Length == 0);
        if (method == null)
        {
            return new { Status = "MethodMissing" };
        }
        try
        {
            var value = method.Invoke(log, Array.Empty<object>());
            return DescribeObject(value, 0);
        }
        catch (TargetInvocationException error)
        {
            return new
            {
                Status = "Failed",
                ExceptionType = (error.InnerException ?? error).GetType().FullName,
                Message = (error.InnerException ?? error).Message,
            };
        }
        catch (Exception error)
        {
            return new
            {
                Status = "Failed",
                ExceptionType = error.GetType().FullName,
                Message = error.Message,
            };
        }
    }

    private static object DescribeObject(object? value, int depth)
    {
        if (value == null)
        {
            return new { Status = "Null" };
        }
        var type = value.GetType();
        var primitive = value is string
            || type.IsPrimitive
            || value is decimal
            || value is DateTime
            || value is DateTimeOffset;
        if (primitive || depth >= 2)
        {
            return new
            {
                Status = "Value",
                Type = type.FullName,
                Value = value.ToString(),
            };
        }
        var result = new Dictionary<string, object?>
        {
            ["Status"] = "Object",
            ["Type"] = type.FullName,
        };
        var props = new Dictionary<string, object?>();
        foreach (var prop in type.GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance).Take(80))
        {
            if (prop.GetIndexParameters().Length > 0)
            {
                continue;
            }
            try
            {
                var propValue = prop.GetValue(value);
                props[prop.Name] = DescribeObject(propValue, depth + 1);
            }
            catch (Exception error)
            {
                props[prop.Name] = new { Status = "Unreadable", Message = error.Message };
            }
        }
        result["Properties"] = props;
        if (value is IEnumerable enumerable && value is not string)
        {
            var items = new List<object?>();
            var count = 0;
            foreach (var item in enumerable)
            {
                if (count >= 5)
                {
                    break;
                }
                items.Add(DescribeObject(item, depth + 1));
                count++;
            }
            result["SampleItems"] = items;
        }
        return result;
    }

    private static object TryReadInteractiveStatistics(string? packagePath)
    {
        if (string.IsNullOrWhiteSpace(packagePath) || !File.Exists(packagePath))
        {
            return new { Status = "Unavailable", Message = "Package path is missing." };
        }
        try
        {
            return ReadInteractiveStatistics(packagePath);
        }
        catch (Exception error)
        {
            return new
            {
                Status = "Failed",
                ExceptionType = error.GetType().FullName,
                Message = error.Message,
            };
        }
    }

    private static object ReadInteractiveStatistics(string packagePath)
    {
        using var archive = ZipFile.OpenRead(packagePath);
        var entry = archive.Entries.FirstOrDefault(e =>
            e.FullName.Replace('\\', '/').Equals(
                "Results/Model/Interactive_Results.stats",
                StringComparison.OrdinalIgnoreCase));
        if (entry == null)
        {
            return new { Status = "Missing", Message = "Interactive_Results.stats was not found." };
        }
        using var stream = entry.Open();
        using var reader = new BinaryReader(stream);
        var stringCount = reader.ReadInt32();
        var strings = new string[stringCount];
        var stringMap = new Dictionary<string, int>();
        for (var index = 0; index < stringCount; index++)
        {
            strings[index] = reader.ReadString();
            if (!stringMap.ContainsKey(strings[index]))
            {
                stringMap[strings[index]] = index;
            }
        }
        var recordCount = reader.ReadInt32();
        var statsType = AppDomain.CurrentDomain
            .GetAssemblies()
            .SelectMany(SafeGetTypes)
            .FirstOrDefault(t => t.FullName == "Simio.Containers.StatisticsReturnValue");
        if (statsType == null)
        {
            return new { Status = "Unavailable", Message = "StatisticsReturnValue type was not found." };
        }
        var method = statsType
            .GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance)
            .FirstOrDefault(m => m.Name == "CreateFromByteStream"
                && m.GetParameters().Length == 4);
        if (method == null)
        {
            return new { Status = "Unavailable", Message = "CreateFromByteStream was not found." };
        }
        var target = method.IsStatic ? null : Activator.CreateInstance(statsType);
        var rows = new List<Dictionary<string, object?>>();
        for (var index = 0; index < recordCount; index++)
        {
            var value = method.Invoke(target, new object?[] { reader, strings, stringMap, null });
            rows.Add(StatisticRow(value, index));
        }
        return new
        {
            Status = "Parsed",
            Source = "Results/Model/Interactive_Results.stats",
            StringCount = stringCount,
            DeclaredRecordCount = recordCount,
            ParsedRecordCount = rows.Count,
            Rows = rows,
        };
    }

    private static Dictionary<string, object?> StatisticRow(object? value, int index)
    {
        var row = new Dictionary<string, object?>
        {
            ["Index"] = index,
            ["RuntimeType"] = value?.GetType().FullName,
        };
        if (value == null)
        {
            return row;
        }
        foreach (var name in new[]
        {
            "ScenarioName",
            "ReplicationNumber",
            "ObjectType",
            "ObjectName",
            "DisplayName",
            "DataSource",
            "TimePeriod",
            "StatisticCategory",
            "StatisticType",
            "DataItem",
            "Value",
            "Average",
            "Minimum",
            "Maximum",
            "HalfWidth",
            "StandardDeviation",
            "StatisticTypeForDisplay",
            "TimePeriodForDisplay",
            "UnitType",
            "IsInteresting",
        })
        {
            var prop = value.GetType().GetProperty(name);
            if (prop == null)
            {
                continue;
            }
            try
            {
                var propValue = prop.GetValue(value);
                row[name] = NormalizeJsonValue(propValue);
            }
            catch
            {
                row[name] = null;
            }
        }
        return row;
    }

    private static object? NormalizeJsonValue(object? value)
    {
        if (value == null)
        {
            return null;
        }
        if (value is double doubleValue)
        {
            return double.IsFinite(doubleValue) ? doubleValue : null;
        }
        if (value is float floatValue)
        {
            return float.IsFinite(floatValue) ? floatValue : null;
        }
        var type = value.GetType();
        if (type.IsPrimitive || value is string || value is decimal)
        {
            return value;
        }
        return value.ToString();
    }

    private static string? GetArg(string[] args, string name)
    {
        for (var index = 0; index < args.Length - 1; index++)
        {
            if (args[index].Equals(name, StringComparison.OrdinalIgnoreCase))
            {
                return args[index + 1];
            }
        }
        return null;
    }

    private static void WriteError(Dictionary<string, object?> result, Exception error)
    {
        result["Status"] = "Failed";
        result["Message"] = error.Message;
        result["ExceptionType"] = error.GetType().FullName;
        result["StackTrace"] = error.StackTrace;
        result["CompletedAt"] = DateTimeOffset.UtcNow.ToString("O");
        WriteJson(result);
    }

    private static void WriteJson(Dictionary<string, object?> result)
    {
        Console.WriteLine(JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = false }));
    }
}
