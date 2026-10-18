--[[
  Jonathan — ustawienia połączenia  (ReaScript, Lua)

  Zmienia adres serwera i token studia, których używa skrypt
  „Jonathan - send rehearsal", i od razu sprawdza połączenie.
  Wyczyszczenie obu pól usuwa zapamiętane ustawienia.
]]

local TITLE = "Jonathan — ustawienia"
local EXT = "JonathanApp"   -- to samo miejsce co w skrypcie wysyłki
local IS_WIN = reaper.GetOS():match("Win") ~= nil

local function trim(s) return (s or ""):match("^%s*(.-)%s*$") end
local function q(s) return '"' .. tostring(s):gsub('"', '') .. '"' end

-- GET {server}/api/studio/ping z tokenem -> (status_http, treść)
local function ping(server, token)
  local tmp = reaper.GetResourcePath() .. (IS_WIN and "\\" or "/") .. "jonathan-ping.json"
  os.remove(tmp)
  local cmd = (IS_WIN and "curl.exe" or "/usr/bin/curl") ..
              " -sS --max-time 20 -o " .. q(tmp) .. " -w " .. q("%{http_code}") ..
              " -H " .. q("Authorization: Bearer " .. token) .. " " .. q(server .. "/api/studio/ping")
  local res = reaper.ExecProcess(cmd, 0) or ""
  local code_line, rest = res:match("^(%-?%d+)\n?(.*)$")
  local f = io.open(tmp, "rb"); local body = f and f:read("*a") or ""; if f then f:close() end
  os.remove(tmp)
  if tonumber(code_line) ~= 0 then return 0, (trim(rest):gsub("^%d%d%d", "")) end
  return tonumber((rest or ""):match("(%d%d%d)%s*$")) or 0, body
end

local server = reaper.GetExtState(EXT, "server")
local token = reaper.GetExtState(EXT, "token")
local ok, vals = reaper.GetUserInputs(TITLE, 2,
  "Adres serwera (https://...),Token studia (jst_...),extrawidth=360",
  (server ~= "" and server or "https://jonathanapp.com") .. "," .. token)
if not ok then return end

local new_server, new_token = vals:match("^([^,]*),(.*)$")
new_server = trim(new_server):gsub("/+$", "")
new_token = trim(new_token)

if new_server == "" and new_token == "" then
  reaper.DeleteExtState(EXT, "server", true)
  reaper.DeleteExtState(EXT, "token", true)
  reaper.ShowMessageBox("Ustawienia usunięte. Przy następnej wysyłce skrypt zapyta o nie od nowa.", TITLE, 0)
  return
end
if new_server == "" or new_token == "" then
  reaper.ShowMessageBox("Podaj i adres serwera, i token.", TITLE, 0)
  return
end

reaper.SetExtState(EXT, "server", new_server, true)
reaper.SetExtState(EXT, "token", new_token, true)

local status, body = ping(new_server, new_token)
local church = body:match('"church"%s*:%s*"(.-)"')
if status == 200 then
  reaper.ShowMessageBox("Zapisane i działa.\n\nPołączono z: " .. new_server ..
    (church and ("\nWspólnota: " .. church) or ""), TITLE, 0)
elseif status == 401 then
  reaper.ShowMessageBox("Zapisane, ale serwer odrzucił token.\n\n" ..
    "Wygeneruj nowy w Jonathanie (Ustawienia → Nagrania z prób) i uruchom te ustawienia jeszcze raz.", TITLE, 0)
else
  reaper.ShowMessageBox("Zapisane, ale nie udało się połączyć z:\n" .. new_server ..
    "\n\n" .. tostring(body):sub(1, 300) .. "\n\nSprawdź adres i połączenie z internetem.", TITLE, 0)
end
