.intel_syntax noprefix

.globl output_link_wrapper_start
.globl output_link_postprocess_start
.globl output_link_final_result_start
.globl output_link_mouseup_charfrompos_done
.globl output_link_mouseup_gettext_done
.globl output_link_mouseup_match_ready
.globl output_link_anchor_visual_start
.globl output_link_cursor_hit
.globl output_link_click_ignore_selection
.globl output_link_click_ignore_drag
.globl output_link_click_open

.set ORIG_RICHEDIT_SET_TEXT_RVA, 0x00008924
.set IAT_SHELLEXECUTEW_RVA, 0x0013E3F4
.set IAT_SETWINDOWLONGW_RVA, 0x0013E548
.set IAT_SCREENTOCLIENT_RVA, 0x0013E5C8
.set IAT_SENDMESSAGEW_RVA, 0x0013E5F4
.set IAT_GETCURSORPOS_RVA, 0x0013E644
.set IAT_LOADCURSORW_RVA, 0x0013E668
.set IAT_SETCURSOR_RVA, 0x0013E66C
.set IAT_CALLWINDOWPROCW_RVA, 0x0013E6A8
.set POPUP_RENDER_RETURN_RVA, 0x00038D58

.set WM_USER, 0x0400
.set WM_GETTEXT, 0x000D
.set WM_GETTEXTLENGTH, 0x000E
.set WM_SETCURSOR, 0x0020
.set WM_LBUTTONDOWN, 0x0201
.set WM_LBUTTONUP, 0x0202
.set EM_SETREADONLY, 0x00CF
.set EM_CHARFROMPOS, 0x00D7
.set EM_EXGETSEL, 0x0434
.set EM_GETEVENTMASK, 0x043B
.set EM_SETEVENTMASK, 0x0445
.set EM_EXSETSEL, 0x0437
.set EM_SETCHARFORMAT, 0x0444
.set SCF_SELECTION, 0x0001
.set CFM_UNDERLINE, 0x00000004
.set CFE_UNDERLINE, 0x00000004
.set CFM_LINK, 0x00000020
.set CFE_LINK, 0x00000020
.set CFM_HIDDEN, 0x00000100
.set CFE_HIDDEN, 0x00000100
.set CFM_COLOR, 0x40000000
.set LINK_COLORREF, 0x00FF0000
.set ENM_LINK, 0x04000000
.set CHARFORMAT2W_SIZE, 116
.set GWL_WNDPROC, -4
.set HTCLIENT, 1
.set IDC_HAND, 0x7F89
.set SW_SHOWNORMAL, 1
.set CLICK_DRAG_TOLERANCE, 3
.set POST_BUF_CHARS, 8191
.set POST_BUF_BYTES, 16384
.set DELTA_SUBCLASS_HWND_FROM_SUBCLASS_IP, output_link_subclass_hwnd - .Lsubclass_ip
.set DELTA_MODULE_BASE_FROM_SUBCLASS_IP, output_link_module_base - .Lsubclass_ip
.set DELTA_RICHEDIT_PROC_FROM_SUBCLASS_PROC_IP, output_link_richedit_proc - .Lsubclass_proc_ip
.set DELTA_OLD_WNDPROC_FROM_SUBCLASS_STORE_IP, output_link_old_wndproc - .Lsubclass_store_ip
.set DELTA_SUBCLASS_HWND_FROM_SUBCLASS_STORE_IP, output_link_subclass_hwnd - .Lsubclass_store_ip
.set DELTA_MODULE_BASE_FROM_PROC_IP, output_link_module_base - .Lproc_ip
.set DELTA_DOWN_HWND_FROM_DOWN_IP, output_link_down_hwnd - .Lproc_down_ip
.set DELTA_DOWN_LPARAM_FROM_DOWN_IP, output_link_down_lparam - .Lproc_down_ip
.set DELTA_DOWN_VALID_FROM_DOWN_IP, output_link_down_valid - .Lproc_down_ip
.set DELTA_DOWN_HWND_FROM_PROC_IP, output_link_down_hwnd - .Lproc_ip
.set DELTA_DOWN_LPARAM_FROM_PROC_IP, output_link_down_lparam - .Lproc_ip
.set DELTA_DOWN_VALID_FROM_PROC_IP, output_link_down_valid - .Lproc_ip
.set DELTA_OLD_WNDPROC_FROM_PROC_OLD_IP_LIGHT, output_link_old_wndproc - .Lproc_old_ip_light
.set DELTA_MODULE_BASE_FROM_PROC_OLD_IP_LIGHT, output_link_module_base - .Lproc_old_ip_light
.set DELTA_MODULE_BASE_FROM_CURSOR_IP, output_link_module_base - .Lcursor_ip
.set DELTA_OLD_WNDPROC_FROM_PROC_OLD_IP, output_link_old_wndproc - .Lproc_old_ip
.set DELTA_MODULE_BASE_FROM_PROC_OLD_IP, output_link_module_base - .Lproc_old_ip

# Wrapper for RichEditCtrl::SetText-like function at 0x408924.
#
# Calling convention of the original:
#   ecx = RichEdit wrapper object
#   [esp+4] = pointer to QTranslate wide string object
#   [esp+8] = mode/kind
#   callee pops 8 bytes
#
# This wrapper calls the original function, then scans the actual RichEdit text
# for "ANCHOR (http...)" / "ANCHOR (www...)" patterns. It applies CFE_LINK
# exactly to the visible anchor and CFE_HIDDEN exactly to the following
# " (url)" suffix.
output_link_wrapper_start:
  push ebp
  mov ebp, esp
  sub esp, 17000
  push ebx
  push esi
  push edi

  mov esi, ecx                  # RichEdit wrapper
  mov edi, [ebp + 8]            # string object pointer
  mov [ebp - 156], esi
  mov [ebp - 160], edi
  mov eax, [ebp + 4]            # caller return address in the rebased module
  sub eax, POPUP_RENDER_RETURN_RVA
  mov [ebp - 168], eax          # runtime module base
  mov edx, [eax + IAT_SENDMESSAGEW_RVA]
  mov [ebp - 172], edx          # rebased SendMessageW import

  push dword ptr [ebp + 12]
  push dword ptr [ebp + 8]
  mov ecx, esi
  mov eax, [ebp - 168]
  add eax, ORIG_RICHEDIT_SET_TEXT_RVA
  call eax

  mov [ebp - 164], eax
  mov esi, [ebp - 156]
  mov edi, [ebp - 160]
  test esi, esi
  jz .Ldone
  mov ebx, [esi + 4]            # HWND
  test ebx, ebx
  jz .Ldone

  # Use the RichEdit's own text as the coordinate source. Its character
  # positions can differ from QTranslate's string buffer after normalization.
  push 0
  push 0
  push WM_GETTEXTLENGTH
  push ebx
  call dword ptr [ebp - 172]
  test eax, eax
  jle .Ldone
  cmp eax, POST_BUF_CHARS
  jle .Llen_ok
  mov eax, POST_BUF_CHARS
.Llen_ok:
  mov [ebp - 136], eax          # text length
  lea edx, [ebp - POST_BUF_BYTES - 256]
  mov [ebp - 132], edx          # text pointer
  push edx
  inc eax
  push eax
  push WM_GETTEXT
  push ebx
  call dword ptr [ebp - 172]

  # Ensure EN_LINK notifications stay enabled if QTranslate handles them.
  push 0
  push 0
  push EM_GETEVENTMASK
  push ebx
  call dword ptr [ebp - 172]
  or eax, ENM_LINK
  push eax
  push 0
  push EM_SETEVENTMASK
  push ebx
  call dword ptr [ebp - 172]

  call .Linstall_click_subclass

  mov eax, [ebp - 136]          # index; scan backwards so hidden ranges do not
  sub eax, 4                    # shift positions for links that appear later.
.Lscan:
  cmp eax, 0
  jl .Ldone
  mov edx, [ebp - 132]
  mov cx, word ptr [edx + eax * 2]
  or cx, 0x20
  cmp cx, 0x72                  # r
  jne .Lmaybe_open_url
  mov cx, word ptr [edx + eax * 2 + 2]
  or cx, 0x20
  cmp cx, 0x65                  # e
  jne .Lnext
  mov cx, word ptr [edx + eax * 2 + 4]
  or cx, 0x20
  cmp cx, 0x61                  # a
  jne .Lnext
  mov cx, word ptr [edx + eax * 2 + 6]
  or cx, 0x20
  cmp cx, 0x64                  # d
  jne .Lnext

  mov [ebp - 140], eax          # linkStart
  lea ecx, [eax + 4]
  mov [ebp - 152], ecx          # linkEnd
  cmp ecx, [ebp - 136]
  jge .Lnext

  # hiddenStart is the first whitespace after READ; support multiple spaces.
  mov edi, ecx
  mov [ebp - 148], edi          # hiddenStart
.Lspace_loop:
  cmp edi, [ebp - 136]
  jge .Lnext
  mov edx, [ebp - 132]
  mov cx, word ptr [edx + edi * 2]
  cmp cx, 0x20
  je .Lspace_advance
  cmp cx, 0x09
  je .Lspace_advance
  jmp .Lrequire_open
.Lspace_advance:
  inc edi
  jmp .Lspace_loop

.Lrequire_open:
  cmp edi, [ebp - 136]
  jge .Lnext
  mov edx, [ebp - 132]
  cmp word ptr [edx + edi * 2], 0x28    # '('
  jne .Lnext
  inc edi                               # URL starts after '('
  lea ecx, [edi + 4]
  cmp ecx, [ebp - 136]
  jge .Lnext

  # Accept http/https and www.
  mov cx, word ptr [edx + edi * 2]
  or cx, 0x20
  cmp cx, 0x68                  # h
  je .Lcheck_read_http
  cmp cx, 0x77                  # w
  je .Lcheck_read_www
  jmp .Lnext

.Lcheck_read_http:
  mov cx, word ptr [edx + edi * 2 + 2]
  or cx, 0x20
  cmp cx, 0x74                  # t
  jne .Lnext
  mov cx, word ptr [edx + edi * 2 + 4]
  or cx, 0x20
  cmp cx, 0x74                  # t
  jne .Lnext
  mov cx, word ptr [edx + edi * 2 + 6]
  or cx, 0x20
  cmp cx, 0x70                  # p
  jne .Lnext
  jmp .Lfind_read_close

.Lcheck_read_www:
  mov cx, word ptr [edx + edi * 2 + 2]
  or cx, 0x20
  cmp cx, 0x77                  # w
  jne .Lnext
  mov cx, word ptr [edx + edi * 2 + 4]
  or cx, 0x20
  cmp cx, 0x77                  # w
  jne .Lnext
  cmp word ptr [edx + edi * 2 + 6], 0x2e # .
  jne .Lnext

.Lfind_read_close:
  inc edi
.Lread_close_loop:
  cmp edi, [ebp - 136]
  jge .Lnext
  mov edx, [ebp - 132]
  cmp word ptr [edx + edi * 2], 0x29    # ')'
  je .Lread_close_found
  inc edi
  jmp .Lread_close_loop

.Lread_close_found:
  inc edi
  mov [ebp - 144], edi          # hiddenEnd

  mov eax, [ebp - 140]
  call .Ltext_index_to_cp
  mov [ebp - 124], eax          # linkStart cp
  mov eax, [ebp - 152]
  call .Ltext_index_to_cp
  mov [ebp - 120], eax          # linkEnd / hiddenStart cp
  mov eax, [ebp - 144]
  call .Ltext_index_to_cp
  mov [ebp - 116], eax          # hiddenEnd cp

  # Link the full backing range so the EN_LINK handler can still recover the
  # hidden URL. The visible part remains only READ because the suffix is hidden.
  push dword ptr [ebp - 172]
  push CFE_LINK
  push CFM_LINK
  push dword ptr [ebp - 116]
  push dword ptr [ebp - 124]
  call .Lapply_format
  add esp, 20

output_link_anchor_visual_start:

  # Re-assert the visible anchor styling on READ only. In practice the
  # backing-range CFE_LINK alone is not sufficient to keep the visible anchor
  # rendered like a hyperlink after the hidden suffix is applied.
  push dword ptr [ebp - 172]
  push dword ptr [ebp - 120]
  push dword ptr [ebp - 124]
  call .Lapply_anchor_visual
  add esp, 12

  # Hide exactly the suffix after READ: spaces + "(url)".
  push dword ptr [ebp - 172]
  push CFE_HIDDEN
  push CFM_HIDDEN
  push dword ptr [ebp - 116]
  push dword ptr [ebp - 120]
  call .Lapply_format
  add esp, 20

.Lafter_format:
  mov eax, [ebp - 140]
  dec eax
  jmp .Lscan

.Lmaybe_open_url:
  mov edx, [ebp - 132]
  cmp word ptr [edx + eax * 2], 0x28    # '('
  jne .Lnext

  mov ecx, eax
  dec ecx
.Lgeneric_back_space:
  cmp ecx, 0
  jl .Lnext
  mov dx, word ptr [edx + ecx * 2]
  cmp dx, 0x20
  je .Lgeneric_back_space_dec
  cmp dx, 0x09
  je .Lgeneric_back_space_dec
  jmp .Lgeneric_have_anchor_end
.Lgeneric_back_space_dec:
  dec ecx
  mov edx, [ebp - 132]
  jmp .Lgeneric_back_space

.Lgeneric_have_anchor_end:
  mov esi, ecx
  inc esi
  mov [ebp - 152], esi          # linkEnd / hiddenStart text index
  mov [ebp - 148], esi
.Lgeneric_back_word:
  cmp ecx, 0
  jl .Lgeneric_start_zero
  mov edx, [ebp - 132]
  mov dx, word ptr [edx + ecx * 2]
  cmp dx, 0x20
  jle .Lgeneric_start_after_delim
  cmp dx, 0x28                  # (
  je .Lgeneric_start_after_delim
  cmp dx, 0x29                  # )
  je .Lgeneric_start_after_delim
  cmp dx, 0x5b                  # [
  je .Lgeneric_start_after_delim
  cmp dx, 0x5d                  # ]
  je .Lgeneric_start_after_delim
  cmp dx, 0x7b                  # {
  je .Lgeneric_start_after_delim
  cmp dx, 0x7d                  # }
  je .Lgeneric_start_after_delim
  cmp dx, 0x2c                  # ,
  je .Lgeneric_start_after_delim
  cmp dx, 0x3b                  # ;
  je .Lgeneric_start_after_delim
  cmp dx, 0x3a                  # :
  je .Lgeneric_start_after_delim
  cmp dx, 0x21                  # !
  je .Lgeneric_start_after_delim
  cmp dx, 0x3f                  # ?
  je .Lgeneric_start_after_delim
  dec ecx
  jmp .Lgeneric_back_word
.Lgeneric_start_zero:
  xor esi, esi
  jmp .Lgeneric_store_start
.Lgeneric_start_after_delim:
  lea esi, [ecx + 1]
.Lgeneric_store_start:
  cmp esi, [ebp - 152]
  jge .Lnext
  mov [ebp - 140], esi          # linkStart text index
  mov edi, eax
  inc edi                       # URL starts after '('
  lea ecx, [edi + 4]
  cmp ecx, [ebp - 136]
  jge .Lnext
  mov edx, [ebp - 132]
  mov cx, word ptr [edx + edi * 2]
  or cx, 0x20
  cmp cx, 0x68                  # h
  je .Lcheck_read_http
  cmp cx, 0x77                  # w
  je .Lcheck_read_www
  jmp .Lnext

.Lnext:
  dec eax
  jmp .Lscan

output_link_postprocess_start:
  ret

# Old broad hooks are intentionally inert. The proven popup path is the single
# RichEdit set-text callsite patched by output_link_wrapper_start.
output_link_final_result_start:
  ret

# Convert a WM_GETTEXT WCHAR index to a RichEdit character position. WM_GETTEXT
# exposes paragraph separators as CRLF, while RichEdit CPs count that pair as
# one character. Input/output: eax.
.Ltext_index_to_cp:
  push ebx
  push ecx
  push edx
  push edi
  mov ebx, eax                  # target text index
  xor ecx, ecx                  # text index
  xor edi, edi                  # RichEdit cp
  mov edx, [ebp - 132]
.Lcp_loop:
  cmp ecx, ebx
  jge .Lcp_done
  cmp word ptr [edx + ecx * 2], 0x0d
  jne .Lcp_normal
  inc edi
  inc ecx
  cmp ecx, ebx
  jge .Lcp_done
  cmp word ptr [edx + ecx * 2], 0x0a
  jne .Lcp_loop
  inc ecx
  jmp .Lcp_loop
.Lcp_normal:
  inc edi
  inc ecx
  jmp .Lcp_loop
.Lcp_done:
  mov eax, edi
  pop edi
  pop edx
  pop ecx
  pop ebx
  ret

.Linstall_click_subclass:
  push eax
  push ecx
  push edx

  call .Lsubclass_ip
.Lsubclass_ip:
  pop edx
  mov ecx, offset DELTA_SUBCLASS_HWND_FROM_SUBCLASS_IP
  cmp dword ptr [edx + ecx], ebx
  je .Linstall_done

  mov eax, [ebp - 168]
  mov ecx, offset DELTA_MODULE_BASE_FROM_SUBCLASS_IP
  mov [edx + ecx], eax
  mov ecx, [eax + IAT_SETWINDOWLONGW_RVA]

  call .Lsubclass_proc_ip
.Lsubclass_proc_ip:
  pop eax
  mov edx, offset DELTA_RICHEDIT_PROC_FROM_SUBCLASS_PROC_IP
  add eax, edx
  push eax
  push GWL_WNDPROC
  push ebx
  call ecx
  test eax, eax
  jz .Linstall_done

  call .Lsubclass_store_ip
.Lsubclass_store_ip:
  pop edx
  mov ecx, offset DELTA_OLD_WNDPROC_FROM_SUBCLASS_STORE_IP
  mov [edx + ecx], eax
  mov ecx, offset DELTA_SUBCLASS_HWND_FROM_SUBCLASS_STORE_IP
  mov [edx + ecx], ebx

.Linstall_done:
  pop edx
  pop ecx
  pop eax
  ret

output_link_richedit_proc:
  push ebp
  mov ebp, esp

  cmp dword ptr [ebp + 12], WM_LBUTTONDOWN
  je .Lproc_mouse_down
  cmp dword ptr [ebp + 12], WM_LBUTTONUP
  je .Lproc_mouse_up
  cmp dword ptr [ebp + 12], WM_SETCURSOR
  je .Lproc_setcursor
  jmp .Lproc_call_old_light

.Lproc_call_old_light:
  call .Lproc_old_ip_light
.Lproc_old_ip_light:
  pop edx
  mov ecx, offset DELTA_OLD_WNDPROC_FROM_PROC_OLD_IP_LIGHT
  mov eax, [edx + ecx]
  test eax, eax
  jz .Lproc_light_zero
  mov ecx, offset DELTA_MODULE_BASE_FROM_PROC_OLD_IP_LIGHT
  mov ecx, [edx + ecx]
  test ecx, ecx
  jz .Lproc_light_zero
  mov ecx, [ecx + IAT_CALLWINDOWPROCW_RVA]
  push dword ptr [ebp + 20]
  push dword ptr [ebp + 16]
  push dword ptr [ebp + 12]
  push dword ptr [ebp + 8]
  push eax
  call ecx
  jmp .Lproc_light_exit
.Lproc_light_zero:
  xor eax, eax
.Lproc_light_exit:
  mov esp, ebp
  pop ebp
  ret 16

.Lproc_mouse_down:
  call .Lproc_down_ip
.Lproc_down_ip:
  pop edx
  mov ecx, offset DELTA_DOWN_HWND_FROM_DOWN_IP
  mov eax, [ebp + 8]
  mov [edx + ecx], eax
  mov ecx, offset DELTA_DOWN_LPARAM_FROM_DOWN_IP
  mov eax, [ebp + 20]
  mov [edx + ecx], eax
  mov ecx, offset DELTA_DOWN_VALID_FROM_DOWN_IP
  mov dword ptr [edx + ecx], 1
  jmp .Lproc_call_old_light

.Lproc_setcursor:
  mov eax, [ebp + 20]
  and eax, 0xffff
  cmp eax, HTCLIENT
  je .Lcursor_client
  jmp .Lproc_call_old_light

.Lcursor_client:
  sub esp, 17000
  push ebx
  push esi
  push edi

  call .Lcursor_ip
.Lcursor_ip:
  pop edi
  mov edx, offset DELTA_MODULE_BASE_FROM_CURSOR_IP
  mov eax, [edi + edx]
  test eax, eax
  jz .Lproc_call_old
  mov [ebp - 168], eax
  mov edx, [eax + IAT_SENDMESSAGEW_RVA]
  mov [ebp - 172], edx

  mov ebx, [ebp + 8]            # hwnd

  lea eax, [ebp - 8]
  push eax
  mov eax, [ebp - 168]
  call dword ptr [eax + IAT_GETCURSORPOS_RVA]
  test eax, eax
  jz .Lproc_call_old

  lea eax, [ebp - 8]
  push eax
  push ebx
  mov eax, [ebp - 168]
  call dword ptr [eax + IAT_SCREENTOCLIENT_RVA]
  test eax, eax
  jz .Lproc_call_old

  lea eax, [ebp - 8]
  push eax
  push 0
  push EM_CHARFROMPOS
  push ebx
  call dword ptr [ebp - 172]
  mov [ebp - 12], eax
  movzx ecx, ax
  mov [ebp - 48], ecx

  push 0
  push 0
  push WM_GETTEXTLENGTH
  push ebx
  call dword ptr [ebp - 172]
  test eax, eax
  jle .Lproc_call_old
  cmp eax, POST_BUF_CHARS
  jle .Lcursor_len_ok
  mov eax, POST_BUF_CHARS
.Lcursor_len_ok:
  mov [ebp - 16], eax
  lea edx, [ebp - POST_BUF_BYTES - 256]
  mov [ebp - 20], edx
  push edx
  inc eax
  push eax
  push WM_GETTEXT
  push ebx
  call dword ptr [ebp - 172]

  xor eax, eax
.Lcursor_scan:
  cmp eax, [ebp - 16]
  jge .Lproc_call_old
  mov edx, [ebp - 20]
  mov cx, word ptr [edx + eax * 2]
  or cx, 0x20
  cmp cx, 0x72
  jne .Lcursor_next
  mov cx, word ptr [edx + eax * 2 + 2]
  or cx, 0x20
  cmp cx, 0x65
  jne .Lcursor_next
  mov cx, word ptr [edx + eax * 2 + 4]
  or cx, 0x20
  cmp cx, 0x61
  jne .Lcursor_next
  mov cx, word ptr [edx + eax * 2 + 6]
  or cx, 0x20
  cmp cx, 0x64
  jne .Lcursor_next

  mov [ebp - 24], eax           # READ text index
  lea ecx, [eax + 4]
  mov [ebp - 28], ecx           # READ end text index
  mov edi, ecx
.Lcursor_space_loop:
  cmp edi, [ebp - 16]
  jge .Lcursor_next
  mov edx, [ebp - 20]
  mov cx, word ptr [edx + edi * 2]
  cmp cx, 0x20
  je .Lcursor_space_advance
  cmp cx, 0x09
  je .Lcursor_space_advance
  jmp .Lcursor_require_open
.Lcursor_space_advance:
  inc edi
  jmp .Lcursor_space_loop

.Lcursor_require_open:
  cmp edi, [ebp - 16]
  jge .Lcursor_next
  mov edx, [ebp - 20]
  cmp word ptr [edx + edi * 2], 0x28
  jne .Lcursor_next
  inc edi
  lea ecx, [edi + 4]
  cmp ecx, [ebp - 16]
  jge .Lcursor_next

  mov cx, word ptr [edx + edi * 2]
  or cx, 0x20
  cmp cx, 0x68
  je .Lcursor_check_http
  cmp cx, 0x77
  je .Lcursor_check_www
  jmp .Lcursor_next

.Lcursor_check_http:
  mov cx, word ptr [edx + edi * 2 + 2]
  or cx, 0x20
  cmp cx, 0x74
  jne .Lcursor_next
  mov cx, word ptr [edx + edi * 2 + 4]
  or cx, 0x20
  cmp cx, 0x74
  jne .Lcursor_next
  mov cx, word ptr [edx + edi * 2 + 6]
  or cx, 0x20
  cmp cx, 0x70
  jne .Lcursor_next
  jmp .Lcursor_have_url

.Lcursor_check_www:
  mov cx, word ptr [edx + edi * 2 + 2]
  or cx, 0x20
  cmp cx, 0x77
  jne .Lcursor_next
  mov cx, word ptr [edx + edi * 2 + 4]
  or cx, 0x20
  cmp cx, 0x77
  jne .Lcursor_next
  cmp word ptr [edx + edi * 2 + 6], 0x2e
  jne .Lcursor_next

.Lcursor_have_url:
  mov eax, [ebp - 24]
  mov esi, [ebp - 20]
  call .Lproc_text_index_to_cp
  mov [ebp - 40], eax
  mov eax, [ebp - 28]
  mov esi, [ebp - 20]
  call .Lproc_text_index_to_cp
  mov [ebp - 44], eax

  mov eax, [ebp - 48]
  cmp eax, [ebp - 40]
  jl .Lcursor_next_from_match
  cmp eax, [ebp - 44]
  jge .Lcursor_next_from_match

output_link_cursor_hit:

  push IDC_HAND
  push 0
  mov eax, [ebp - 168]
  call dword ptr [eax + IAT_LOADCURSORW_RVA]
  test eax, eax
  jz .Lproc_call_old
  push eax
  mov edx, [ebp - 168]
  call dword ptr [edx + IAT_SETCURSOR_RVA]
  mov eax, 1
  jmp .Lproc_exit

.Lcursor_next_from_match:
  mov eax, [ebp - 24]
.Lcursor_next:
  inc eax
  jmp .Lcursor_scan

.Lproc_mouse_up:
  sub esp, 17000
  push ebx
  push esi
  push edi

  call .Lproc_ip
.Lproc_ip:
  pop edi
  mov edx, offset DELTA_MODULE_BASE_FROM_PROC_IP
  mov eax, [edi + edx]
  test eax, eax
  jz .Lproc_call_old
  mov [ebp - 168], eax
  mov edx, [eax + IAT_SENDMESSAGEW_RVA]
  mov [ebp - 172], edx

  mov ebx, [ebp + 8]            # hwnd

  # Only treat a mouse-up as a link click if it belongs to the same button
  # press and did not become a drag/selection gesture.
  mov edx, offset DELTA_DOWN_VALID_FROM_PROC_IP
  cmp dword ptr [edi + edx], 1
  jne .Lproc_call_old
  mov dword ptr [edi + edx], 0
  mov edx, offset DELTA_DOWN_HWND_FROM_PROC_IP
  mov eax, [edi + edx]
  cmp eax, ebx
  jne .Lproc_call_old

  mov eax, [ebp + 20]
  movsx ecx, ax                 # mouse-up x
  mov edx, offset DELTA_DOWN_LPARAM_FROM_PROC_IP
  mov eax, [edi + edx]
  movsx edx, ax                 # mouse-down x
  sub ecx, edx
  jge .Lproc_dx_abs
  neg ecx
.Lproc_dx_abs:
  cmp ecx, CLICK_DRAG_TOLERANCE
  jg output_link_click_ignore_drag

  mov eax, [ebp + 20]
  sar eax, 16                   # mouse-up y
  mov ecx, eax
  mov edx, offset DELTA_DOWN_LPARAM_FROM_PROC_IP
  mov eax, [edi + edx]
  sar eax, 16                   # mouse-down y
  sub ecx, eax
  jge .Lproc_dy_abs
  neg ecx
.Lproc_dy_abs:
  cmp ecx, CLICK_DRAG_TOLERANCE
  jg output_link_click_ignore_drag

  lea eax, [ebp - 64]           # CHARRANGE { cpMin, cpMax }
  push eax
  push 0
  push EM_EXGETSEL
  push ebx
  call dword ptr [ebp - 172]
  mov eax, [ebp - 64]
  cmp eax, [ebp - 60]
  jne output_link_click_ignore_selection

  # lParam carries client x/y. EM_CHARFROMPOS expects a POINTL pointer and is
  # safe here because the subclass runs inside QTranslate's process.
  mov eax, [ebp + 20]
  movsx ecx, ax
  mov [ebp - 8], ecx
  sar eax, 16
  mov [ebp - 4], eax
  lea eax, [ebp - 8]
  push eax
  push 0
  push EM_CHARFROMPOS
  push ebx
  call dword ptr [ebp - 172]
  mov [ebp - 12], eax           # raw EM_CHARFROMPOS result
  movzx ecx, ax
  mov [ebp - 48], ecx           # normalized RichEdit cp from low word

output_link_mouseup_charfrompos_done:

  push 0
  push 0
  push WM_GETTEXTLENGTH
  push ebx
  call dword ptr [ebp - 172]
  test eax, eax
  jle .Lproc_call_old
  cmp eax, POST_BUF_CHARS
  jle .Lproc_len_ok
  mov eax, POST_BUF_CHARS
.Lproc_len_ok:
  mov [ebp - 16], eax
  lea edx, [ebp - POST_BUF_BYTES - 256]
  mov [ebp - 20], edx
  push edx
  inc eax
  push eax
  push WM_GETTEXT
  push ebx
  call dword ptr [ebp - 172]

output_link_mouseup_gettext_done:

  xor eax, eax
.Lproc_scan:
  cmp eax, [ebp - 16]
  jge .Lproc_call_old
  mov edx, [ebp - 20]
  mov cx, word ptr [edx + eax * 2]
  or cx, 0x20
  cmp cx, 0x72                  # r
  jne .Lproc_next
  mov cx, word ptr [edx + eax * 2 + 2]
  or cx, 0x20
  cmp cx, 0x65                  # e
  jne .Lproc_next
  mov cx, word ptr [edx + eax * 2 + 4]
  or cx, 0x20
  cmp cx, 0x61                  # a
  jne .Lproc_next
  mov cx, word ptr [edx + eax * 2 + 6]
  or cx, 0x20
  cmp cx, 0x64                  # d
  jne .Lproc_next

  mov [ebp - 24], eax           # linkStart text index
  lea ecx, [eax + 4]
  mov [ebp - 28], ecx           # linkEnd text index
  mov edi, ecx
.Lproc_space_loop:
  cmp edi, [ebp - 16]
  jge .Lproc_next
  mov edx, [ebp - 20]
  mov cx, word ptr [edx + edi * 2]
  cmp cx, 0x20
  je .Lproc_space_advance
  cmp cx, 0x09
  je .Lproc_space_advance
  jmp .Lproc_require_open
.Lproc_space_advance:
  inc edi
  jmp .Lproc_space_loop

.Lproc_require_open:
  cmp edi, [ebp - 16]
  jge .Lproc_next
  mov edx, [ebp - 20]
  cmp word ptr [edx + edi * 2], 0x28    # '('
  jne .Lproc_next
  inc edi
  mov [ebp - 36], edi           # URL text index
  lea ecx, [edi + 4]
  cmp ecx, [ebp - 16]
  jge .Lproc_next

  mov cx, word ptr [edx + edi * 2]
  or cx, 0x20
  cmp cx, 0x68
  je .Lproc_check_http
  cmp cx, 0x77
  je .Lproc_check_www
  jmp .Lproc_next

.Lproc_check_http:
  mov cx, word ptr [edx + edi * 2 + 2]
  or cx, 0x20
  cmp cx, 0x74
  jne .Lproc_next
  mov cx, word ptr [edx + edi * 2 + 4]
  or cx, 0x20
  cmp cx, 0x74
  jne .Lproc_next
  mov cx, word ptr [edx + edi * 2 + 6]
  or cx, 0x20
  cmp cx, 0x70
  jne .Lproc_next
  jmp .Lproc_find_close

.Lproc_check_www:
  mov cx, word ptr [edx + edi * 2 + 2]
  or cx, 0x20
  cmp cx, 0x77
  jne .Lproc_next
  mov cx, word ptr [edx + edi * 2 + 4]
  or cx, 0x20
  cmp cx, 0x77
  jne .Lproc_next
  cmp word ptr [edx + edi * 2 + 6], 0x2e
  jne .Lproc_next

.Lproc_find_close:
  inc edi
.Lproc_close_loop:
  cmp edi, [ebp - 16]
  jge .Lproc_next
  mov edx, [ebp - 20]
  cmp word ptr [edx + edi * 2], 0x29
  je .Lproc_close_found
  inc edi
  jmp .Lproc_close_loop

.Lproc_close_found:
  mov [ebp - 32], edi           # closing ')' text index

  mov eax, [ebp - 24]
  mov esi, [ebp - 20]
  call .Lproc_text_index_to_cp
  mov [ebp - 40], eax
  mov eax, [ebp - 28]
  mov esi, [ebp - 20]
  call .Lproc_text_index_to_cp
  mov [ebp - 44], eax

  mov eax, [ebp - 48]
  cmp eax, [ebp - 40]
  jl .Lproc_next_from_match
  cmp eax, [ebp - 44]
  jge .Lproc_next_from_match

  mov edx, [ebp - 20]
  mov ecx, [ebp - 32]
  mov word ptr [edx + ecx * 2], 0
  mov eax, [ebp - 36]
  lea eax, [edx + eax * 2]
  mov [ebp - 52], eax

output_link_mouseup_match_ready:

output_link_click_open:

  mov edx, [ebp - 168]
  mov edx, [edx + IAT_SHELLEXECUTEW_RVA]
  push SW_SHOWNORMAL
  push 0
  push 0
  push eax
  push 0
  push ebx
  call edx
  jmp .Lproc_call_old

output_link_click_ignore_selection:
  jmp .Lproc_call_old

output_link_click_ignore_drag:
  jmp .Lproc_call_old

.Lproc_next_from_match:
  mov eax, [ebp - 24]
.Lproc_next:
  inc eax
  jmp .Lproc_scan

.Lproc_call_old:
  call .Lproc_old_ip
.Lproc_old_ip:
  pop edi
  mov edx, offset DELTA_OLD_WNDPROC_FROM_PROC_OLD_IP
  mov eax, [edi + edx]
  test eax, eax
  jz .Lproc_zero
  mov edx, offset DELTA_MODULE_BASE_FROM_PROC_OLD_IP
  mov ecx, [edi + edx]
  test ecx, ecx
  jz .Lproc_zero
  mov ecx, [ecx + IAT_CALLWINDOWPROCW_RVA]
  push dword ptr [ebp + 20]
  push dword ptr [ebp + 16]
  push dword ptr [ebp + 12]
  push dword ptr [ebp + 8]
  push eax
  call ecx
  jmp .Lproc_exit

.Lproc_zero:
  xor eax, eax

.Lproc_exit:
  pop edi
  pop esi
  pop ebx
  mov esp, ebp
  pop ebp
  ret 16

# Input: eax = WM_GETTEXT WCHAR index, esi = text pointer. Output: eax = RichEdit cp.
.Lproc_text_index_to_cp:
  push ebx
  push ecx
  push edx
  push edi
  mov ebx, eax
  xor ecx, ecx
  xor edi, edi
.Lproc_cp_loop:
  cmp ecx, ebx
  jge .Lproc_cp_done
  cmp word ptr [esi + ecx * 2], 0x0d
  jne .Lproc_cp_normal
  inc edi
  inc ecx
  cmp ecx, ebx
  jge .Lproc_cp_done
  cmp word ptr [esi + ecx * 2], 0x0a
  jne .Lproc_cp_loop
  inc ecx
  jmp .Lproc_cp_loop
.Lproc_cp_normal:
  inc edi
  inc ecx
  jmp .Lproc_cp_loop
.Lproc_cp_done:
  mov eax, edi
  pop edi
  pop edx
  pop ecx
  pop ebx
  ret

  .align 4
output_link_old_wndproc:
  .long 0
output_link_subclass_hwnd:
  .long 0
output_link_module_base:
  .long 0
output_link_down_hwnd:
  .long 0
output_link_down_lparam:
  .long 0
output_link_down_valid:
  .long 0

# Args:
#   [esp+4]  = start
#   [esp+8]  = end
#   [esp+12] = mask
#   [esp+16] = effects
#   [esp+20] = SendMessageW
.Lapply_format:
  push ebp
  mov ebp, esp
  sub esp, 136

  push 0
  push 0
  push EM_SETREADONLY
  push ebx
  mov eax, [ebp + 24]
  call eax

  mov eax, [ebp + 8]
  mov [ebp - 136], eax
  mov eax, [ebp + 12]
  mov [ebp - 132], eax
  lea eax, [ebp - 136]
  push eax
  push 0
  push EM_EXSETSEL
  push ebx
  mov eax, [ebp + 24]
  call eax

  lea edi, [ebp - 128]
  xor eax, eax
  mov ecx, 29
  rep stosd
  mov dword ptr [ebp - 128], CHARFORMAT2W_SIZE
  mov eax, [ebp + 16]
  mov [ebp - 124], eax
  mov eax, [ebp + 20]
  mov [ebp - 120], eax
  lea eax, [ebp - 128]
  push eax
  push SCF_SELECTION
  push EM_SETCHARFORMAT
  push ebx
  mov eax, [ebp + 24]
  call eax

  mov esp, ebp
  pop ebp
  ret

# Args:
#   [esp+4]  = start
#   [esp+8]  = end
#   [esp+12] = SendMessageW
.Lapply_anchor_visual:
  push ebp
  mov ebp, esp
  sub esp, 136

  push 0
  push 0
  push EM_SETREADONLY
  push ebx
  mov eax, [ebp + 16]
  call eax

  mov eax, [ebp + 8]
  mov [ebp - 136], eax
  mov eax, [ebp + 12]
  mov [ebp - 132], eax
  lea eax, [ebp - 136]
  push eax
  push 0
  push EM_EXSETSEL
  push ebx
  mov eax, [ebp + 16]
  call eax

  lea edi, [ebp - 128]
  xor eax, eax
  mov ecx, 29
  rep stosd
  mov dword ptr [ebp - 128], CHARFORMAT2W_SIZE
  mov dword ptr [ebp - 124], CFM_LINK | CFM_HIDDEN | CFM_UNDERLINE | CFM_COLOR
  mov dword ptr [ebp - 120], CFE_LINK | CFE_UNDERLINE
  mov dword ptr [ebp - 108], LINK_COLORREF
  lea eax, [ebp - 128]
  push eax
  push SCF_SELECTION
  push EM_SETCHARFORMAT
  push ebx
  mov eax, [ebp + 16]
  call eax

  mov esp, ebp
  pop ebp
  ret

.Ldone:
  mov eax, [ebp - 164]
  pop edi
  pop esi
  pop ebx
  mov esp, ebp
  pop ebp
  ret 8
