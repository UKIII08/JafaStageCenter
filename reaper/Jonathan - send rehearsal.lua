--[[
  Jonathan — wyślij próbę  (ReaScript, Lua)

  Wysyła nagranie z próby do aranżacji w Jonathanie:
    * cały miks,
    * dla każdego śladu "J:<partia>":  "miks + partia głośniej"  i  "miks bez partii".

  Nazewnictwo w projekcie:
    Region   = piosenka        "Oceany"  albo  "Oceany | Akustyczna"
    Markery  = kafelki formy   "Intro", "Z1", "Refren", "Bridge" ... (w regionie)
    Ślady    = partie          "J:Wokal 2", "J:Gitara"  (ślady bez "J:" są pomijane)

  Jeśli jest zaznaczony zakres czasu, wysyłane są tylko regiony w tym zakresie.
  Format pliku bierze się z ostatnich ustawień File → Render (zalecane MP3 128–192 kb/s).
  Przy pierwszym uruchomieniu skrypt pyta o adres serwera i token studia
  (Jonathan → Ustawienia → Nagrania z prób).
  Zmiana adresu lub tokenu: akcja „Jonathan - settings" (drugi skrypt). Okno pojawi
  się też samo, gdy serwer odrzuci token albo nie da się z nim połączyć.
  (Z rozszerzeniem js_ReaScriptAPI działa też uruchomienie z wciśniętym Shift.)

  Wymaga: REAPER 6.x+, curl (wbudowany w Windows 10/11 i macOS).
]]

local TITLE = "Jonathan — wyślij próbę"
local EXT = "JonathanApp"
local LOUD_GAIN = 2.0          -- +6 dB dla "miks + ja głośniej"
local IS_WIN = reaper.GetOS():match("Win") ~= nil
local SEP = IS_WIN and "\\" or "/"

---------------------------------------------------------------- JSON (mini)
local json = {}
do
  local esc = { ['"'] = '\\"', ['\\'] = '\\\\', ['\b'] = '\\b', ['\f'] = '\\f',
                ['\n'] = '\\n', ['\r'] = '\\r', ['\t'] = '\\t' }
  local function enc(v)
    local t = type(v)
    if t == "nil" then return "null"
    elseif t == "boolean" then return v and "true" or "false"
    elseif t == "number" then return string.format("%.3f", v)
    elseif t == "string" then
      return '"' .. v:gsub('[%c"\\]', function(c)
        return esc[c] or string.format("\\u%04x", c:byte())
      end) .. '"'
    elseif t == "table" then
      if v.__array or v[1] ~= nil then
        local out = {}
        for _, x in ipairs(v) do out[#out + 1] = enc(x) end
        return "[" .. table.concat(out, ",") .. "]"
      end
      local out = {}
      for k, x in pairs(v) do
        if k ~= "__array" then out[#out + 1] = enc(tostring(k)) .. ":" .. enc(x) end
      end
      return "{" .. table.concat(out, ",") .. "}"
    end
    error("json: nieobsługiwany typ " .. t)
  end
  json.encode = enc
  function json.array(t) t = t or {}; t.__array = true; return t end

  function json.decode(s)
    local i = 1
    local function ws() i = s:find("[^ \t\r\n]", i) or #s + 1 end
    local val
    local function str()
      i = i + 1
      local out = {}
      while true do
        local c = s:sub(i, i)
        if c == "" then error("json: niezamknięty napis") end
        if c == '"' then i = i + 1; break end
        if c == "\\" then
          local n = s:sub(i + 1, i + 1)
          local map = { b = "\b", f = "\f", n = "\n", r = "\r", t = "\t" }
          if n == "u" then
            local cp = tonumber(s:sub(i + 2, i + 5), 16)
            if cp >= 0xD800 and cp <= 0xDBFF and s:sub(i + 6, i + 7) == "\\u" then
              local lo = tonumber(s:sub(i + 8, i + 11), 16)
              cp = 0x10000 + (cp - 0xD800) * 0x400 + (lo - 0xDC00)
              i = i + 6
            end
            out[#out + 1] = utf8.char(cp)
            i = i + 6
          else
            out[#out + 1] = map[n] or n
            i = i + 2
          end
        else
          out[#out + 1] = c
          i = i + 1
        end
      end
      return table.concat(out)
    end
    function val()
      ws()
      local c = s:sub(i, i)
      if c == "{" then
        i = i + 1
        local o = {}
        ws()
        if s:sub(i, i) == "}" then i = i + 1; return o end
        while true do
          ws(); local k = str(); ws()
          i = i + 1           -- ':'
          o[k] = val(); ws()
          local d = s:sub(i, i); i = i + 1
          if d == "}" then return o end
        end
      elseif c == "[" then
        i = i + 1
        local a = {}
        ws()
        if s:sub(i, i) == "]" then i = i + 1; return a end
        while true do
          a[#a + 1] = val(); ws()
          local d = s:sub(i, i); i = i + 1
          if d == "]" then return a end
        end
      elseif c == '"' then return str()
      elseif s:sub(i, i + 3) == "true" then i = i + 4; return true
      elseif s:sub(i, i + 4) == "false" then i = i + 5; return false
      elseif s:sub(i, i + 3) == "null" then i = i + 4; return nil
      else
        local num = s:match("^-?%d+%.?%d*[eE]?[-+]?%d*", i)
        if not num or num == "" then error("json: błąd przy znaku " .. i) end
        i = i + #num
        return tonumber(num)
      end
    end
    return val()
  end
end

---------------------------------------------------------------- pliki i curl
local function trim(s) return (s or ""):match("^%s*(.-)%s*$") end

local TMP = reaper.GetResourcePath() .. SEP .. "Jonathan"
reaper.RecursiveCreateDirectory(TMP, 0)

local function write_file(path, data)
  local f = assert(io.open(path, "wb")); f:write(data); f:close()
end
local function read_file(path)
  local f = io.open(path, "rb"); if not f then return nil end
  local d = f:read("*a"); f:close(); return d
end
local function q(s) return '"' .. tostring(s):gsub('"', '') .. '"' end

-- Wywołanie curl; zwraca (status_http, treść_odpowiedzi)
local function curl(args)
  local out = TMP .. SEP .. "response.json"
  os.remove(out)
  local cmd = (IS_WIN and "curl.exe" or "/usr/bin/curl") ..
              " -sS --max-time 600 -o " .. q(out) .. " -w " .. q("%{http_code}") .. " " .. args
  local res = reaper.ExecProcess(cmd, 0)
  if not res then return 0, "curl nie wystartował" end
  local code_line, rest = res:match("^(%-?%d+)\n?(.*)$")
  local status = tonumber((rest or ""):match("(%d%d%d)%s*$")) or 0
  if tonumber(code_line) ~= 0 then return 0, trim(rest) end
  return status, read_file(out) or ""
end

---------------------------------------------------------------- konfiguracja
local function config(force)
  local server = reaper.GetExtState(EXT, "server")
  local token = reaper.GetExtState(EXT, "token")
  if force or server == "" or token == "" then
    local ok, vals = reaper.GetUserInputs(TITLE, 2,
      "Adres serwera (https://...),Token studia (jst_...),extrawidth=360",
      (server ~= "" and server or "https://jonathanapp.com") .. "," .. token)
    if not ok then return nil end
    server, token = vals:match("^([^,]*),(.*)$")
    server = trim(server):gsub("/+$", "")
    token = trim(token)
    if server == "" or token == "" then return nil end
    reaper.SetExtState(EXT, "server", server, true)
    reaper.SetExtState(EXT, "token", token, true)
  end
  return server, token
end

local function api(server, token, method, path, body)
  local auth = "-H " .. q("Authorization: Bearer " .. token)
  local args = auth
  if body then
    local bf = TMP .. SEP .. "request.json"
    write_file(bf, json.encode(body))
    args = args .. " -X " .. method .. " -H " .. q("Content-Type: application/json") ..
           " --data-binary " .. q("@" .. bf)
  end
  local status, text = curl(args .. " " .. q(server .. path))
  local ok, data = pcall(json.decode, text ~= "" and text or "null")
  return status, ok and data or nil, text
end

local function upload(server, token, arr_id, kind, role, file)
  -- Rola idzie z pliku tekstowego (UTF-8) — polskie znaki bez kłopotów z kodowaniem.
  local rf = TMP .. SEP .. "role.txt"
  write_file(rf, role or "")
  local args = "-H " .. q("Authorization: Bearer " .. token) ..
               " -F " .. q("kind=" .. kind) ..
               " -F " .. q("role=<" .. rf) ..
               " -F " .. q("file=@" .. file) .. " " ..
               q(server .. "/api/studio/arrangements/" .. arr_id .. "/file")
  return curl(args)
end

---------------------------------------------------------------- projekt
local function collect()
  local ts, te = reaper.GetSet_LoopTimeRange(false, false, 0, 0, false)
  local use_sel = te > ts
  local regions, markers = {}, {}
  local i = 0
  while true do
    local ret, isrgn, pos, rgnend, name = reaper.EnumProjectMarkers3(0, i)
    if ret == 0 then break end
    if isrgn then
      if (not use_sel) or (pos < te and rgnend > ts) then
        regions[#regions + 1] = { name = trim(name), start = pos, stop = rgnend }
      end
    else
      markers[#markers + 1] = { name = trim(name), pos = pos }
    end
    i = i + 1
  end
  table.sort(markers, function(a, b) return a.pos < b.pos end)
  for _, r in ipairs(regions) do
    local inside = {}
    for _, m in ipairs(markers) do
      if m.pos >= r.start - 0.001 and m.pos < r.stop and m.name ~= "" then
        inside[#inside + 1] = m
      end
    end
    r.markers = json.array()
    for k, m in ipairs(inside) do
      local stop = inside[k + 1] and inside[k + 1].pos or r.stop
      r.markers[#r.markers + 1] = { name = m.name, start = m.pos - r.start, ["end"] = stop - r.start }
    end
  end
  local tracks = {}
  for t = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, t)
    local _, name = reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "", false)
    local role = name:match("^%s*[Jj]%s*:%s*(.-)%s*$")
    if role and role ~= "" then tracks[#tracks + 1] = { track = tr, role = role } end
  end
  return regions, tracks
end

---------------------------------------------------------------- render
local SAVE_KEYS = { "RENDER_SETTINGS", "RENDER_BOUNDSFLAG", "RENDER_STARTPOS",
                    "RENDER_ENDPOS", "RENDER_ADDTOPROJ" }
local SAVE_STR = { "RENDER_FILE", "RENDER_PATTERN" }
local EXTS = { "mp3", "ogg", "opus", "m4a", "flac", "wav" }

local function save_render()
  local s = { num = {}, str = {} }
  for _, k in ipairs(SAVE_KEYS) do s.num[k] = reaper.GetSetProjectInfo(0, k, 0, false) end
  for _, k in ipairs(SAVE_STR) do
    local _, v = reaper.GetSetProjectInfo_String(0, k, "", false); s.str[k] = v
  end
  return s
end
local function restore_render(s)
  for k, v in pairs(s.num) do reaper.GetSetProjectInfo(0, k, v, true) end
  for k, v in pairs(s.str) do reaper.GetSetProjectInfo_String(0, k, v, true) end
end

local function render(name, start, stop)
  for _, e in ipairs(EXTS) do os.remove(TMP .. SEP .. name .. "." .. e) end
  reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)      -- miks z mastera
  reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 0, true)    -- własny zakres
  reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", start, true)
  reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", stop, true)
  reaper.GetSetProjectInfo(0, "RENDER_ADDTOPROJ", 0, true)
  reaper.GetSetProjectInfo_String(0, "RENDER_FILE", TMP, true)
  reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", name, true)
  reaper.Main_OnCommand(42230, 0)   -- Render project, using the most recent render settings, auto-close
  for _, e in ipairs(EXTS) do
    local p = TMP .. SEP .. name .. "." .. e
    if reaper.file_exists(p) then return p end
  end
  return nil
end

---------------------------------------------------------------- główny przebieg
local function fmt_region(r)
  local lines = {}
  if not r.ok then
    lines[#lines + 1] = "✗ " .. r.region .. " — nie ma takiej piosenki w Jonathanie (pominięty)"
    return table.concat(lines, "\n")
  end
  lines[#lines + 1] = "• " .. r.song_title .. "  →  " .. r.arrangement ..
                      (r.create and "  (nowa wersja)" or "")
  if r.markers > 0 then
    if r.form_differs then
      lines[#lines + 1] = "    Kafelki: " .. r.tiles_matched .. "/" .. r.tiles ..
                          " — forma zostanie ustawiona wg markerów (" .. r.markers .. ")"
    else
      lines[#lines + 1] = "    Kafelki: " .. r.tiles_matched .. "/" .. r.tiles .. " ✓"
    end
  else
    lines[#lines + 1] = "    Brak markerów — bez podziału na kafelki"
  end
  local parts = {}
  for _, t in ipairs(r.tracks or {}) do
    parts[#parts + 1] = "J:" .. t.track .. (t.role and " ✓" or " (nowa partia)")
  end
  lines[#lines + 1] = "    Ślady: " .. (#parts > 0 and table.concat(parts, ", ") or "tylko miks")
  return table.concat(lines, "\n")
end

local function main()
  -- Shift przy uruchomieniu = zmień adres/token (wymaga rozszerzenia js_ReaScriptAPI;
  -- bez niego okno pojawi się samo, gdy token przestanie działać).
  local force = false
  if reaper.JS_Mouse_GetState then force = (reaper.JS_Mouse_GetState(8) & 8) == 8 end
  local server, token = config(force)
  if not server then return end

  local regions, tracks = collect()
  if #regions == 0 then
    reaper.ShowMessageBox("Nie znalazłem regionów.\n\nZaznacz każdą piosenkę jako region " ..
      "nazwany jak w Jonathanie (np. \"Oceany\" albo \"Oceany | Akustyczna\").", TITLE, 0)
    return
  end
  local track_names = json.array()
  for _, t in ipairs(tracks) do track_names[#track_names + 1] = t.role end

  local req = { regions = json.array() }
  for _, r in ipairs(regions) do
    req.regions[#req.regions + 1] = { name = r.name, markers = r.markers, tracks = track_names }
  end
  local status, plan, raw = api(server, token, "POST", "/api/studio/plan", req)
  if status == 401 then
    reaper.ShowMessageBox("Token studia jest nieprawidłowy albo został unieważniony.\n" ..
      "Wygeneruj nowy w Jonathanie (Ustawienia → Nagrania z prób) i wklej go.", TITLE, 0)
    config(true)
    return
  end
  if status ~= 200 or not plan then
    -- Zły adres (np. został stary) albo brak sieci — daj od razu poprawić ustawienia.
    local again = reaper.ShowMessageBox("Nie udało się połączyć z:\n" .. server ..
      "\n\n" .. trim(tostring(raw)):gsub("^%d%d%d", ""):sub(1, 300) ..
      "\n\nZmienić adres serwera lub token?", TITLE, 4)
    if again == 6 then config(true) end
    return
  end

  local _, fmt = reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "", false)
  local warn = ""
  if fmt:sub(1, 6) == "ZXZhdw" then
    warn = "\n\nUWAGA: format renderu to WAV — pliki będą duże. Lepiej ustaw MP3 w File → Render."
  end

  local lines, todo = {}, 0
  for k, r in ipairs(plan.regions) do
    lines[#lines + 1] = fmt_region(r)
    if r.ok then todo = todo + 1 end
    r.local_region = regions[k]
  end
  if todo == 0 then
    reaper.ShowMessageBox(table.concat(lines, "\n\n"), TITLE, 0)
    return
  end
  local n_files = todo * (1 + 2 * #tracks)
  local msg = "Wspólnota: " .. (plan.church or "?") .. "   (" .. server .. ")\n\n" .. table.concat(lines, "\n\n") ..
              "\n\nDo wyrenderowania i wysłania: " .. n_files .. " plików. " ..
              "Poprzednie nagrania tych wersji zostaną zastąpione." .. warn
  if reaper.ShowMessageBox(msg, TITLE, 1) ~= 1 then return end

  local saved = save_render()
  local sent, errors = 0, {}
  reaper.PreventUIRefresh(1)
  local ok, err = pcall(function()
    for _, r in ipairs(plan.regions) do
      if r.ok then
        local reg = r.local_region
        local st, res = api(server, token, "POST", "/api/studio/commit", {
          song_id = r.song_id, version = r.version or "", markers = reg.markers,
          tracks = track_names, duration = reg.stop - reg.start })
        if st ~= 200 or not res then
          errors[#errors + 1] = r.song_title .. ": nie udało się przygotować wersji (" .. st .. ")"
        else
          local function send(kind, role, file)
            if not file then
              errors[#errors + 1] = r.song_title .. ": render " .. kind .. " " .. (role or "") .. " nie powstał"
              return
            end
            local s2 = upload(server, token, res.arrangement_id, kind, role, file)
            if s2 == 200 then sent = sent + 1
            else errors[#errors + 1] = r.song_title .. ": " .. kind .. " " .. (role or "") .. " (" .. s2 .. ")" end
            os.remove(file)
          end
          send("mix", "", render("mix", reg.start, reg.stop))
          for _, t in ipairs(tracks) do
            local role = (res.roles and res.roles[t.role]) or t.role
            local vol = reaper.GetMediaTrackInfo_Value(t.track, "D_VOL")
            local mute = reaper.GetMediaTrackInfo_Value(t.track, "B_MUTE")
            reaper.SetMediaTrackInfo_Value(t.track, "B_MUTE", 0)
            reaper.SetMediaTrackInfo_Value(t.track, "D_VOL", vol * LOUD_GAIN)
            local loud = render("loud", reg.start, reg.stop)
            reaper.SetMediaTrackInfo_Value(t.track, "D_VOL", vol)
            reaper.SetMediaTrackInfo_Value(t.track, "B_MUTE", 1)
            local minus = render("minus", reg.start, reg.stop)
            reaper.SetMediaTrackInfo_Value(t.track, "B_MUTE", mute)
            send("loud", role, loud)
            send("minus", role, minus)
          end
        end
      end
    end
  end)
  restore_render(saved)
  reaper.PreventUIRefresh(-1)
  reaper.UpdateArrange()

  local summary = "Wysłano plików: " .. sent .. " z " .. n_files .. "."
  if not ok then errors[#errors + 1] = "Błąd skryptu: " .. tostring(err) end
  if #errors > 0 then summary = summary .. "\n\nProblemy:\n" .. table.concat(errors, "\n") end
  reaper.ShowMessageBox(summary, TITLE, 0)
end

main()
