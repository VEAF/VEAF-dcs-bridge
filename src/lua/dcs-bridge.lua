--[[
dcs-bridge — Lua bridge for DCS World
https://github.com/VEAF/dcs-bridge

Installation — choose one method:

  Method A (MissionScripting.lua):
    dcsBridge = { host = "localhost", port = 7777 }
    dofile(lfs.writedir().."Scripts\\dcs-bridge.lua")

  Method B (Mission trigger "DO SCRIPT FILE"):
    Add a trigger at mission start with condition ONCE / time = 0:
      action "DO SCRIPT":  dcsBridge = { host = "localhost", port = 7777 }
      action "DO SCRIPT FILE": <path to dcs-bridge.lua>

Configuration keys (all optional, shown with defaults):
  dcsBridge.host                 = "127.0.0.1"
  dcsBridge.port                 = 7777
  dcsBridge.fullRefreshInterval  = 5       -- seconds between full unit snapshots
  dcsBridge.reconnectBackoffMax  = 60      -- max backoff in seconds
  dcsBridge.reconnectWarnAfter   = 30      -- warn in log after N seconds without connection

Dependencies:
  - LuaSocket (bundled with DCS)
  - Scripts/JSON.lua (bundled with DCS)
  - MIST (only required for the "spawn" command)
]]--

do
    -- -------------------------------------------------------------------------
    -- Configuration defaults
    -- -------------------------------------------------------------------------
    if not dcsBridge then dcsBridge = {} end
    dcsBridge.host                = dcsBridge.host               or "127.0.0.1"
    dcsBridge.port                = dcsBridge.port               or 7777
    dcsBridge.fullRefreshInterval = dcsBridge.fullRefreshInterval or 5
    dcsBridge.reconnectBackoffMax = dcsBridge.reconnectBackoffMax or 60
    dcsBridge.reconnectWarnAfter  = dcsBridge.reconnectWarnAfter  or 30

    -- -------------------------------------------------------------------------
    -- Dependencies
    -- -------------------------------------------------------------------------
    package.path  = package.path  .. ";.\\LuaSocket\\?.lua"
    package.cpath = package.cpath .. ";.\\LuaSocket\\?.dll"
    local socket = require("socket")
    local JSON   = loadfile("Scripts\\JSON.lua")()

    -- -------------------------------------------------------------------------
    -- Internal state
    -- -------------------------------------------------------------------------
    local _connected          = false
    local _conn               = nil
    local _txbuf              = ""
    local _lastFullRefresh    = 0
    local _lastConnectAttempt = -math.huge  -- attempt immediately on first step
    local _firstDisconnectAt  = nil
    local _warnedDisconnect   = false
    local _backoff            = 1

    -- -------------------------------------------------------------------------
    -- Logging helpers
    -- -------------------------------------------------------------------------
    local function log(msg)
        env.info("[dcs-bridge] " .. tostring(msg))
    end

    local function logWarning(msg)
        env.warning("[dcs-bridge] " .. tostring(msg))
    end

    -- -------------------------------------------------------------------------
    -- Protocol helpers
    -- -------------------------------------------------------------------------

    -- Append a message table to the TX buffer as a JSON line.
    local function enqueue(msg)
        local ok, encoded = pcall(function()
            return JSON:encode(msg):gsub("\n", "") .. "\n"
        end)
        if ok then
            _txbuf = _txbuf .. encoded
        else
            log("JSON encode error: " .. tostring(encoded))
        end
    end

    -- -------------------------------------------------------------------------
    -- Capability detection (ADR-0005)
    -- -------------------------------------------------------------------------

    -- Probe the frameworks loaded in the running mission and their versions.
    -- Absent frameworks are simply omitted; DCS is always present so serve
    -- infers it without an explicit entry.
    local function detectFrameworks()
        local fw = {}
        if mist then
            if mist.majorVersion then
                fw.mist = string.format("%s.%s.%s",
                    tostring(mist.majorVersion),
                    tostring(mist.minorVersion or 0),
                    tostring(mist.build or 0))
            else
                fw.mist = tostring(mist.version or "unknown")
            end
        end
        if ctld then
            fw.ctld = tostring(ctld.Version or ctld.VERSION or "unknown")
        end
        if veaf then
            fw.veaf = tostring(veaf.BuildVersion or veaf.Version or veaf.MainVersion or "unknown")
        end
        return fw
    end

    -- Announce detected capabilities. Called on every (re)connect.
    local function sendHandshake()
        enqueue({ type = "handshake", frameworks = detectFrameworks() })
    end

    -- -------------------------------------------------------------------------
    -- Unit data builder
    -- -------------------------------------------------------------------------

    local CATEGORY_NAMES = {
        [Unit.Category.GROUND_UNIT] = "vehicle",
        [Unit.Category.AIRPLANE]    = "plane",
        [Unit.Category.HELICOPTER]  = "helicopter",
        [Unit.Category.SHIP]        = "ship",
    }

    -- Returns a unit data table or nil if the unit is not observable.
    local function buildUnit(unit)
        if not unit or not unit:isExist() or not unit:isActive() then return nil end
        local pos = unit:getPosition()
        -- ADR-0001: coordinate conversion done here via DCS native API
        local lat, lon = coord.LOtoLL(pos.p)
        local agl = pos.p.y - land.getHeight({ x = pos.p.x, y = pos.p.z })
        local desc = unit:getDesc()
        return {
            name         = unit:getName(),
            position_dcs = { x = pos.p.x, y = pos.p.y, z = pos.p.z },
            position_geo = { lat = lat, lon = lon },
            altitude_agl = agl,
            category     = CATEGORY_NAMES[desc and desc.category] or "unknown",
            type         = unit:getTypeName(),
            coalition    = unit:getCoalition(),
        }
    end

    -- -------------------------------------------------------------------------
    -- Full refresh
    -- -------------------------------------------------------------------------

    -- Collect all alive units across all coalitions and push a full_refresh message.
    local function sendFullRefresh()
        local units = {}
        for _, side in ipairs({ coalition.side.RED, coalition.side.BLUE, coalition.side.NEUTRAL }) do
            local groups = coalition.getGroups(side)
            if groups then
                for _, group in ipairs(groups) do
                    local groupUnits = group:getUnits()
                    if groupUnits then
                        for _, unit in ipairs(groupUnits) do
                            local data = buildUnit(unit)
                            if data then units[#units + 1] = data end
                        end
                    end
                end
            end
        end
        enqueue({ type = "full_refresh", units = units })
    end

    -- -------------------------------------------------------------------------
    -- Command handlers
    -- -------------------------------------------------------------------------

    local function handleExec(msg)
        local code = msg.payload and msg.payload.code
        if not code then
            enqueue({ id = msg.id, result = nil, error = "missing payload.code" })
            return
        end
        local f, compileErr = loadstring(code)
        if not f then
            enqueue({ id = msg.id, result = nil, error = tostring(compileErr) })
            return
        end
        local ok, result = pcall(f)
        if ok then
            enqueue({ id = msg.id, result = tostring(result ~= nil and result or ""), error = nil })
        else
            enqueue({ id = msg.id, result = nil, error = tostring(result) })
        end
    end

    local function handleSpawn(msg)
        local group = msg.payload and msg.payload.group
        if not group then
            enqueue({ id = msg.id, result = nil, error = "missing payload.group" })
            return
        end
        -- spawn requires MIST (http://github.com/mrSkortch/MissionScriptingTools)
        if not mist or not mist.dynAdd then
            enqueue({ id = msg.id, result = nil, error = "spawn requires MIST to be loaded before dcs-bridge" })
            return
        end
        local ok, err = pcall(mist.dynAdd, group)
        if ok then
            enqueue({ id = msg.id, result = "spawned", error = nil })
        else
            enqueue({ id = msg.id, result = nil, error = tostring(err) })
        end
    end

    local COMMAND_HANDLERS = {
        exec  = handleExec,
        spawn = handleSpawn,
    }

    local function handleCommand(msg)
        local handler = COMMAND_HANDLERS[msg.action]
        if handler then
            pcall(handler, msg)
        else
            log("unknown action: " .. tostring(msg.action))
        end
    end

    -- -------------------------------------------------------------------------
    -- Connection management (exponential backoff — ADR-0003)
    -- -------------------------------------------------------------------------

    local function disconnect()
        _connected = false
        if _conn then _conn:close() end
        _conn = nil
        _txbuf = ""
    end

    local function tryConnect()
        local now = timer.getTime()
        if now - _lastConnectAttempt < _backoff then return end
        _lastConnectAttempt = now

        -- track time since first disconnect for warning threshold
        if _firstDisconnectAt == nil then _firstDisconnectAt = now end
        local disconnectedFor = now - _firstDisconnectAt
        if not _warnedDisconnect and disconnectedFor >= dcsBridge.reconnectWarnAfter then
            logWarning(string.format(
                "no connection for %ds — retrying every %ds (max backoff %ds) (target: %s:%d)",
                math.floor(disconnectedFor), _backoff, dcsBridge.reconnectBackoffMax,
                dcsBridge.host, dcsBridge.port
            ))
            _warnedDisconnect = true
        end

        _conn = socket.tcp()
        _conn:settimeout(0.0001)
        _conn:connect(dcsBridge.host, dcsBridge.port)
        -- send() / receive() will confirm the connection; treat any data exchange as connected
        _connected = true
        _lastFullRefresh = 0  -- force immediate full refresh on (re)connect
        sendHandshake()       -- announce capabilities on every (re)connect
    end

    local function onDisconnect(reason)
        log("disconnected: " .. tostring(reason))
        disconnect()
        -- reset warning state for the new disconnection window
        _warnedDisconnect = false
        -- exponential backoff, capped
        _backoff = math.min(_backoff * 2, dcsBridge.reconnectBackoffMax)
    end

    -- -------------------------------------------------------------------------
    -- Main step (called every 100ms via timer.scheduleFunction)
    -- -------------------------------------------------------------------------

    local function step()
        if not _connected then
            tryConnect()
            return
        end

        -- send full refresh on schedule
        local now = timer.getTime()
        if now - _lastFullRefresh >= dcsBridge.fullRefreshInterval then
            local ok, err = pcall(sendFullRefresh)
            if not ok then log("full refresh error: " .. tostring(err)) end
            _lastFullRefresh = now
        end

        -- flush TX buffer
        if _txbuf ~= "" then
            local sent, sendErr, partial = _conn:send(_txbuf)
            if sent then
                _txbuf = _txbuf:sub(sent + 1)
            else
                _txbuf = _txbuf:sub((partial or 0) + 1)
                if sendErr == "closed" or (partial or 0) == 0 then
                    onDisconnect("send error: " .. tostring(sendErr))
                    return
                end
            end
        end

        -- read one incoming command per step (non-blocking)
        local line, recvErr = _conn:receive()
        if line then
            -- reset backoff and warning state on successful communication
            _backoff = 1
            _firstDisconnectAt = nil
            _warnedDisconnect = false
            local ok, msg = pcall(JSON.decode, JSON, line)
            if ok and msg then
                handleCommand(msg)
            else
                log("JSON decode error: " .. tostring(msg))
            end
        elseif recvErr == "closed" then
            onDisconnect("server closed connection")
        end
        -- recvErr == "timeout" is expected with non-blocking socket — ignore
    end

    -- -------------------------------------------------------------------------
    -- Bootstrap
    -- -------------------------------------------------------------------------

    log(string.format("initializing — connecting to %s:%d", dcsBridge.host, dcsBridge.port))

    timer.scheduleFunction(function(_, time)
        local ok, err = pcall(step)
        if not ok then log("step error: " .. tostring(err)) end
        return time + 0.1
    end, nil, timer.getTime() + 0.1)
end
