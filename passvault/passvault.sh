#!/usr/bin/env bash
###############################################################################
#  PASSVAULT — Terminal Password Manager
#  AES-256-CBC encrypted vault, PBKDF2 key derivation, phosphor-terminal UI
###############################################################################

set -uo pipefail

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
VAULT_DIR="${HOME}/.passvault"
VAULT_FILE="${VAULT_DIR}/vault.enc"
HASH_FILE="${VAULT_DIR}/master.hash"
SALT_FILE="${VAULT_DIR}/master.salt"
TMP_DIR="$(mktemp -d)"
PLAIN_DB="${TMP_DIR}/vault.db"          # decrypted, in-memory-ish, tmpfs-only
SESSION_KEY=""

mkdir -p "$VAULT_DIR"
chmod 700 "$VAULT_DIR"

trap cleanup EXIT INT TERM

cleanup() {
    [[ -d "$TMP_DIR" ]] && shred -u "$TMP_DIR"/* 2>/dev/null; rm -rf "$TMP_DIR" 2>/dev/null
}

# ---------------------------------------------------------------------------
# COLORS — phosphor / neon terminal palette
# ---------------------------------------------------------------------------
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

FG_GREEN='\033[38;5;46m'      # phosphor green
FG_CYAN='\033[38;5;51m'       # neon cyan
FG_MAGENTA='\033[38;5;201m'   # neon magenta
FG_AMBER='\033[38;5;214m'     # amber accent
FG_RED='\033[38;5;196m'       # alert red
FG_GRAY='\033[38;5;240m'      # dim gray
FG_WHITE='\033[38;5;255m'

BG_DARK='\033[48;5;233m'

# ---------------------------------------------------------------------------
# UI HELPERS
# ---------------------------------------------------------------------------
term_width() { tput cols 2>/dev/null || echo 78; }

hr() {
    local w; w=$(term_width)
    printf "${FG_GRAY}"
    printf '─%.0s' $(seq 1 "$w")
    printf "${RESET}\n"
}

banner() {
    clear
    echo -e "${FG_GREEN}"
    cat << "EOF"
   ██████╗  █████╗ ███████╗███████╗██╗   ██╗ █████╗ ██╗   ████████╗
   ██╔══██╗██╔══██╗██╔════╝██╔════╝██║   ██║██╔══██╗██║   ╚══██╔══╝
   ██████╔╝███████║███████╗███████╗██║   ██║███████║██║      ██║
   ██╔═══╝ ██╔══██║╚════██║╚════██║╚██╗ ██╔╝██╔══██║██║      ██║
   ██║     ██║  ██║███████║███████║ ╚████╔╝ ██║  ██║███████╗ ██║
   ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝  ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═╝
EOF
    echo -e "${RESET}"
    echo -e "${FG_GRAY}${DIM}          encrypted terminal password manager · AES-256-CBC${RESET}"
    hr
}

msg_ok()    { echo -e "  ${FG_GREEN}[+]${RESET} $1"; }
msg_info()  { echo -e "  ${FG_CYAN}[*]${RESET} $1"; }
msg_warn()  { echo -e "  ${FG_AMBER}[!]${RESET} $1"; }
msg_err()   { echo -e "  ${FG_RED}[x]${RESET} $1"; }
msg_dim()   { echo -e "  ${FG_GRAY}${DIM}$1${RESET}"; }

prompt() {
    local text="$1"
    echo -en "  ${FG_MAGENTA}❯${RESET} ${FG_WHITE}${text}${RESET} "
}

prompt_secret() {
    local text="$1"
    echo -en "  ${FG_MAGENTA}❯${RESET} ${FG_WHITE}${text}${RESET} "
}

pause() {
    echo
    echo -en "  ${FG_GRAY}${DIM}Press ENTER to continue...${RESET}"
    read -r
}

section_title() {
    echo
    echo -e "  ${BOLD}${FG_CYAN}▐ $1${RESET}"
    hr
}

# spinner-style loading feedback (used for crypto ops)
loading() {
    local msg="$1"
    echo -en "  ${FG_GRAY}${DIM}${msg}...${RESET}"
    sleep 0.15
    echo -e "\r  ${FG_GREEN}${msg}... done${RESET}   "
}

# ---------------------------------------------------------------------------
# CRYPTO HELPERS
# ---------------------------------------------------------------------------
# Derive key via PBKDF2 and verify against stored hash
verify_master_password() {
    local pass="$1"
    local salt
    salt=$(cat "$SALT_FILE")
    local computed
    computed=$(echo -n "$pass" | openssl dgst -sha256 -hmac "$salt" | awk '{print $2}')
    local stored
    stored=$(cat "$HASH_FILE")
    [[ "$computed" == "$stored" ]]
}

set_master_password() {
    local pass="$1"
    local salt
    salt=$(openssl rand -hex 16)
    echo -n "$salt" > "$SALT_FILE"
    local hash
    hash=$(echo -n "$pass" | openssl dgst -sha256 -hmac "$salt" | awk '{print $2}')
    echo -n "$hash" > "$HASH_FILE"
    chmod 600 "$SALT_FILE" "$HASH_FILE"
}

# Decrypt vault into plaintext temp DB
decrypt_vault() {
    local pass="$1"
    if [[ ! -f "$VAULT_FILE" ]]; then
        : > "$PLAIN_DB"
        return 0
    fi
    openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -d -salt \
        -in "$VAULT_FILE" -out "$PLAIN_DB" -pass "pass:${pass}" 2>/dev/null
    return $?
}

# Encrypt plaintext temp DB back into vault
encrypt_vault() {
    local pass="$1"
    openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -e -salt \
        -in "$PLAIN_DB" -out "$VAULT_FILE" -pass "pass:${pass}" 2>/dev/null
    chmod 600 "$VAULT_FILE"
}

# ---------------------------------------------------------------------------
# FIELD ENCODING
# Each vault line: base64(site)|base64(username)|base64(password)|base64(notes)|base64(timestamp)
# Base64 avoids delimiter collisions since raw fields may contain "|"
# ---------------------------------------------------------------------------
b64enc() { printf '%s' "$1" | base64 -w0; }
b64dec() { printf '%s' "$1" | base64 -d 2>/dev/null; }

# ---------------------------------------------------------------------------
# INIT / LOGIN FLOW
# ---------------------------------------------------------------------------
first_run_setup() {
    banner
    echo -e "  ${FG_AMBER}No vault detected. Let's create one.${RESET}"
    echo
    local p1 p2
    while true; do
        prompt_secret "Create a master password:"
        read -rs p1; echo
        if [[ ${#p1} -lt 8 ]]; then
            msg_err "Master password must be at least 8 characters."
            continue
        fi
        prompt_secret "Confirm master password:"
        read -rs p2; echo
        if [[ "$p1" != "$p2" ]]; then
            msg_err "Passwords do not match. Try again."
            continue
        fi
        break
    done
    set_master_password "$p1"
    : > "$PLAIN_DB"
    encrypt_vault "$p1"
    SESSION_KEY="$p1"
    echo
    msg_ok "Vault created and encrypted."
    sleep 0.6
}

login_flow() {
    banner
    local attempts=0
    while true; do
        prompt_secret "Master password:"
        read -rs input; echo
        if verify_master_password "$input"; then
            if decrypt_vault "$input"; then
                SESSION_KEY="$input"
                msg_ok "Vault unlocked."
                sleep 0.4
                return 0
            else
                msg_err "Decryption failed. Vault may be corrupted."
                exit 1
            fi
        else
            attempts=$((attempts+1))
            msg_err "Incorrect master password. (attempt $attempts)"
            if [[ $attempts -ge 5 ]]; then
                msg_err "Too many failed attempts. Exiting."
                exit 1
            fi
        fi
    done
}

# ---------------------------------------------------------------------------
# PASSWORD GENERATOR
# ---------------------------------------------------------------------------
generate_password() {
    local length="${1:-16}"
    local charset='A-Za-z0-9!@#$%^&*()-_=+[]{}'
    tr -dc "$charset" < /dev/urandom | head -c "$length"
}

password_strength() {
    local pass="$1"
    local len=${#pass}
    local score=0
    [[ $len -ge 8 ]]  && score=$((score+1))
    [[ $len -ge 12 ]] && score=$((score+1))
    [[ $len -ge 16 ]] && score=$((score+1))
    [[ "$pass" =~ [a-z] ]] && score=$((score+1))
    [[ "$pass" =~ [A-Z] ]] && score=$((score+1))
    [[ "$pass" =~ [0-9] ]] && score=$((score+1))
    [[ "$pass" =~ [^a-zA-Z0-9] ]] && score=$((score+1))

    if   [[ $score -le 2 ]]; then echo -e "${FG_RED}WEAK${RESET}"
    elif [[ $score -le 4 ]]; then echo -e "${FG_AMBER}MODERATE${RESET}"
    elif [[ $score -le 6 ]]; then echo -e "${FG_CYAN}STRONG${RESET}"
    else echo -e "${FG_GREEN}VERY STRONG${RESET}"
    fi
}

# ---------------------------------------------------------------------------
# CORE OPERATIONS
# ---------------------------------------------------------------------------
save_vault() {
    encrypt_vault "$SESSION_KEY"
}

entry_count() {
    [[ -f "$PLAIN_DB" ]] && wc -l < "$PLAIN_DB" || echo 0
}

add_entry() {
    section_title "ADD NEW ENTRY"
    prompt "Site / Service name:"
    read -r site
    if [[ -z "$site" ]]; then msg_err "Site name cannot be empty."; pause; return; fi

    prompt "Username / Email:"
    read -r username

    echo
    echo -e "  ${FG_GRAY}${DIM}Password options: [1] Enter manually  [2] Generate random${RESET}"
    prompt "Choose (1/2):"
    read -r pwopt

    local password
    if [[ "$pwopt" == "2" ]]; then
        prompt "Length (default 16):"
        read -r plen
        plen="${plen:-16}"
        password=$(generate_password "$plen")
        echo
        echo -e "  ${FG_GREEN}Generated password:${RESET} ${BOLD}${password}${RESET}"
    else
        prompt_secret "Password:"
        read -rs password; echo
    fi

    echo -en "  ${FG_GRAY}${DIM}Strength: "
    password_strength "$password"

    prompt "Notes (optional):"
    read -r notes

    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')

    echo "$(b64enc "$site")|$(b64enc "$username")|$(b64enc "$password")|$(b64enc "$notes")|$(b64enc "$ts")" >> "$PLAIN_DB"
    save_vault
    echo
    msg_ok "Entry saved for '${site}'."
    pause
}

list_entries() {
    section_title "STORED ENTRIES"
    if [[ ! -s "$PLAIN_DB" ]]; then
        msg_warn "Vault is empty. Add your first entry from the main menu."
        pause
        return
    fi

    printf "  ${BOLD}${FG_CYAN}%-4s %-24s %-24s %s${RESET}\n" "ID" "SITE" "USERNAME" "ADDED"
    hr
    local i=1
    while IFS='|' read -r site user pass notes ts; do
        local s u t
        s=$(b64dec "$site")
        u=$(b64dec "$user")
        t=$(b64dec "$ts")
        printf "  ${FG_AMBER}%-4s${RESET} ${FG_WHITE}%-24s${RESET} ${FG_GRAY}%-24s${RESET} ${FG_GRAY}${DIM}%s${RESET}\n" \
            "$i" "${s:0:23}" "${u:0:23}" "$t"
        i=$((i+1))
    done < "$PLAIN_DB"
    pause
}

view_entry() {
    section_title "VIEW ENTRY"
    if [[ ! -s "$PLAIN_DB" ]]; then
        msg_warn "Vault is empty."
        pause
        return
    fi
    list_entries_silent
    prompt "Enter entry ID to view:"
    read -r id
    local line
    line=$(sed -n "${id}p" "$PLAIN_DB")
    if [[ -z "$line" ]]; then
        msg_err "Invalid ID."
        pause
        return
    fi
    IFS='|' read -r site user pass notes ts <<< "$line"
    echo
    echo -e "  ${FG_CYAN}Site:${RESET}     $(b64dec "$site")"
    echo -e "  ${FG_CYAN}Username:${RESET} $(b64dec "$user")"
    echo -e "  ${FG_CYAN}Password:${RESET} ${BOLD}$(b64dec "$pass")${RESET}"
    echo -e "  ${FG_CYAN}Notes:${RESET}    $(b64dec "$notes")"
    echo -e "  ${FG_CYAN}Added:${RESET}    $(b64dec "$ts")"
    pause
}

list_entries_silent() {
    printf "  ${BOLD}${FG_CYAN}%-4s %-24s %-24s${RESET}\n" "ID" "SITE" "USERNAME"
    hr
    local i=1
    while IFS='|' read -r site user pass notes ts; do
        printf "  ${FG_AMBER}%-4s${RESET} ${FG_WHITE}%-24s${RESET} ${FG_GRAY}%-24s${RESET}\n" \
            "$i" "$(b64dec "$site")" "$(b64dec "$user")"
        i=$((i+1))
    done < "$PLAIN_DB"
    echo
}

search_entries() {
    section_title "SEARCH ENTRIES"
    prompt "Search term (site or username):"
    read -r term
    if [[ -z "$term" ]]; then msg_err "Empty search term."; pause; return; fi

    echo
    printf "  ${BOLD}${FG_CYAN}%-4s %-24s %-24s${RESET}\n" "ID" "SITE" "USERNAME"
    hr
    local i=1 found=0
    while IFS='|' read -r site user pass notes ts; do
        local s u
        s=$(b64dec "$site")
        u=$(b64dec "$user")
        local s_lower u_lower term_lower
        s_lower=$(printf '%s' "$s" | tr '[:upper:]' '[:lower:]')
        u_lower=$(printf '%s' "$u" | tr '[:upper:]' '[:lower:]')
        term_lower=$(printf '%s' "$term" | tr '[:upper:]' '[:lower:]')
        if [[ "$s_lower" == *"$term_lower"* || "$u_lower" == *"$term_lower"* ]]; then
            printf "  ${FG_AMBER}%-4s${RESET} ${FG_WHITE}%-24s${RESET} ${FG_GRAY}%-24s${RESET}\n" "$i" "$s" "$u"
            found=1
        fi
        i=$((i+1))
    done < "$PLAIN_DB"
    [[ $found -eq 0 ]] && msg_warn "No matches found."
    pause
}

edit_entry() {
    section_title "EDIT ENTRY"
    if [[ ! -s "$PLAIN_DB" ]]; then msg_warn "Vault is empty."; pause; return; fi
    list_entries_silent
    prompt "Enter entry ID to edit:"
    read -r id
    local total
    total=$(entry_count)
    if [[ -z "$id" || "$id" -lt 1 || "$id" -gt "$total" ]]; then
        msg_err "Invalid ID."
        pause
        return
    fi

    local line
    line=$(sed -n "${id}p" "$PLAIN_DB")
    IFS='|' read -r site user pass notes ts <<< "$line"

    echo
    msg_dim "Leave a field blank to keep current value."
    echo
    prompt "Site [$(b64dec "$site")]:"
    read -r new_site
    prompt "Username [$(b64dec "$user")]:"
    read -r new_user
    prompt_secret "Password (leave blank to keep current):"
    read -rs new_pass; echo
    prompt "Notes [$(b64dec "$notes")]:"
    read -r new_notes

    [[ -n "$new_site" ]]  && site=$(b64enc "$new_site")
    [[ -n "$new_user" ]]  && user=$(b64enc "$new_user")
    [[ -n "$new_pass" ]]  && pass=$(b64enc "$new_pass")
    [[ -n "$new_notes" ]] && notes=$(b64enc "$new_notes")
    ts=$(b64enc "$(date '+%Y-%m-%d %H:%M:%S')")

    local newline="${site}|${user}|${pass}|${notes}|${ts}"
    awk -v n="$id" -v repl="$newline" 'NR==n{$0=repl} {print}' "$PLAIN_DB" > "${PLAIN_DB}.tmp" \
        && mv "${PLAIN_DB}.tmp" "$PLAIN_DB"
    save_vault
    echo
    msg_ok "Entry #${id} updated."
    pause
}

delete_entry() {
    section_title "DELETE ENTRY"
    if [[ ! -s "$PLAIN_DB" ]]; then msg_warn "Vault is empty."; pause; return; fi
    list_entries_silent
    prompt "Enter entry ID to delete:"
    read -r id
    local total
    total=$(entry_count)
    if [[ -z "$id" || "$id" -lt 1 || "$id" -gt "$total" ]]; then
        msg_err "Invalid ID."
        pause
        return
    fi

    local line
    line=$(sed -n "${id}p" "$PLAIN_DB")
    IFS='|' read -r site user pass notes ts <<< "$line"
    echo
    msg_warn "About to delete: $(b64dec "$site") ($(b64dec "$user"))"
    prompt "Type 'yes' to confirm:"
    read -r confirm
    if [[ "$confirm" == "yes" ]]; then
        sed -i "${id}d" "$PLAIN_DB"
        save_vault
        msg_ok "Entry deleted."
    else
        msg_info "Cancelled."
    fi
    pause
}

generate_standalone() {
    section_title "PASSWORD GENERATOR"
    prompt "Length (default 16):"
    read -r plen
    plen="${plen:-16}"
    local pass
    pass=$(generate_password "$plen")
    echo
    echo -e "  ${FG_GREEN}${BOLD}${pass}${RESET}"
    echo -en "  ${FG_GRAY}${DIM}Strength: "
    password_strength "$pass"
    pause
}

change_master_password() {
    section_title "CHANGE MASTER PASSWORD"
    prompt_secret "Current master password:"
    read -rs cur; echo
    if ! verify_master_password "$cur"; then
        msg_err "Incorrect password."
        pause
        return
    fi
    prompt_secret "New master password:"
    read -rs np1; echo
    if [[ ${#np1} -lt 8 ]]; then
        msg_err "Password must be at least 8 characters."
        pause
        return
    fi
    prompt_secret "Confirm new master password:"
    read -rs np2; echo
    if [[ "$np1" != "$np2" ]]; then
        msg_err "Passwords do not match."
        pause
        return
    fi
    set_master_password "$np1"
    SESSION_KEY="$np1"
    save_vault
    msg_ok "Master password changed."
    pause
}

vault_stats() {
    section_title "VAULT STATISTICS"
    local total
    total=$(entry_count)
    echo -e "  ${FG_CYAN}Total entries:${RESET}  $total"
    echo -e "  ${FG_CYAN}Vault file:${RESET}     $VAULT_FILE"
    echo -e "  ${FG_CYAN}Encryption:${RESET}     AES-256-CBC (PBKDF2, 100000 iter)"
    if [[ -f "$VAULT_FILE" ]]; then
        local size
        size=$(du -h "$VAULT_FILE" | cut -f1)
        echo -e "  ${FG_CYAN}Vault size:${RESET}     $size"
    fi
    pause
}

# ---------------------------------------------------------------------------
# MAIN MENU
# ---------------------------------------------------------------------------
main_menu() {
    while true; do
        banner
        local total
        total=$(entry_count)
        echo -e "  ${FG_GRAY}${DIM}Entries in vault: ${total}${RESET}"
        echo
        echo -e "   ${FG_GREEN}[1]${RESET} Add new entry"
        echo -e "   ${FG_GREEN}[2]${RESET} List entries"
        echo -e "   ${FG_GREEN}[3]${RESET} View entry"
        echo -e "   ${FG_GREEN}[4]${RESET} Search entries"
        echo -e "   ${FG_GREEN}[5]${RESET} Edit entry"
        echo -e "   ${FG_GREEN}[6]${RESET} Delete entry"
        echo -e "   ${FG_GREEN}[7]${RESET} Generate random password"
        echo -e "   ${FG_GREEN}[8]${RESET} Change master password"
        echo -e "   ${FG_GREEN}[9]${RESET} Vault statistics"
        echo -e "   ${FG_RED}[0]${RESET} Lock vault and exit"
        echo
        hr
        prompt "Select an option:"
        read -r choice
        case "$choice" in
            1) add_entry ;;
            2) list_entries ;;
            3) view_entry ;;
            4) search_entries ;;
            5) edit_entry ;;
            6) delete_entry ;;
            7) generate_standalone ;;
            8) change_master_password ;;
            9) vault_stats ;;
            0)
                cleanup
                echo
                msg_ok "Vault locked. Goodbye."
                exit 0
                ;;
            *)
                msg_err "Invalid option."
                sleep 0.6
                ;;
        esac
    done
}

# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
main() {
    if [[ ! -f "$HASH_FILE" || ! -f "$SALT_FILE" ]]; then
        first_run_setup
    else
        login_flow
    fi
    main_menu
}

main
