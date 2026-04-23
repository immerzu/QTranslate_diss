.intel_syntax noprefix
.section .text
.globl shellcode_start
.globl accessibility_shellcode_start
.globl accessibility_shellcode_delegate_start
.globl accessibility_shellcode_noop_start
.globl accessibility_shellcode_name_only_start
.globl accessibility_shellcode_uia_point_start

.set CAVE_RVA, 0x0013D0A3
.set RVA_GET_BASE, CAVE_RVA + .Lget_base - shellcode_start
.set RVA_ACC_GET_BASE, CAVE_RVA + .Lacc_get_base - shellcode_start
.set RVA_CLIP_OWNER, 0x0018421C
.set RVA_OPEN_CLIP_GUARD, 0x0003BDD3
.set RVA_CLEAR_WIDE, 0x00002478
.set RVA_ORIGINAL_ACCESSIBILITY, 0x00003901
.set RVA_ASSIGN_WIDE, 0x00002231
.set RVA_IAT_LOADLIBEXA, 0x0013E148
.set RVA_IAT_GETPROCADDRESS, 0x0013E308
.set RVA_IAT_GETCLIPBOARDDATA, 0x0013E594
.set RVA_IAT_GETCURSORPOS, 0x0013E644
.set RVA_IAT_ACCESSIBLEOBJECTFROMPOINT, 0x0013E394
.set RVA_IAT_VARIANTINIT, 0x0013E3A0
.set RVA_IAT_VARIANTCLEAR, 0x0013E3A4
.set RVA_IAT_SYSSTRINGLEN, 0x0013E3A8
.set RVA_IAT_SYSFREESTRING, 0x0013E3B4
.set RVA_IAT_COINITIALIZEEX, 0x0013E804
.set RVA_IAT_COCREATEINSTANCE, 0x0013E808
.set RVA_IAT_COUNINITIALIZE, 0x0013E818
.set RVA_IAT_GLOBALSIZE, 0x0013E2C8
.set RVA_IAT_GLOBALLOCK, 0x0013E2C4
.set RVA_IAT_GLOBALALLOC, 0x0013E2BC
.set RVA_IAT_GLOBALFREE, 0x0013E2B8
.set RVA_IAT_GLOBALUNLOCK, 0x0013E2C0
.set RVA_IAT_CLOSECLIPBOARD, 0x0013E468
.set RVA_ACC_READY_FLAG, 0x0018454C

.set STR_USER32_OFF, .Lstr_user32 - .Lget_base
.set STR_REGFMT_OFF, .Lstr_regfmt - .Lget_base
.set STR_HTMLFMT_OFF, .Lstr_htmlfmt - .Lget_base
.set STR_STARTFRAG_OFF, .Lstr_startfrag - .Lget_base
.set STR_ENDFRAG_OFF, .Lstr_endfrag - .Lget_base
.set STR_HTTP_OFF_ACC, .Lstr_http - .Lacc_get_base
.set STR_HTTPS_OFF_ACC, .Lstr_https - .Lacc_get_base
.set STR_FTP_OFF_ACC, .Lstr_ftp - .Lacc_get_base
.set STR_FILE_OFF_ACC, .Lstr_file - .Lacc_get_base
.set STR_MAILTO_OFF_ACC, .Lstr_mailto - .Lacc_get_base
.set ACC_UIA_DATA_BASE_DELTA, .Lacc_get_base - .Lacc_uia_get_base
.set GUID_CUIAUTOMATION_OFF_ACC, .Lguid_clsid_cuiautomation - .Lacc_get_base
.set GUID_IUIAUTOMATION_OFF_ACC, .Lguid_iid_iuiautomation - .Lacc_get_base
.set GUID_IUIAUTOMATIONVALUEPATTERN_OFF_ACC, .Lguid_iid_iuiautomationvaluepattern - .Lacc_get_base

# Replacement for 0x43BE7E (thiscall):
#   ecx = output string object
#   edx = max chars (0 = unlimited)
#
# Strategy:
# 1. Open clipboard with the existing guard helper.
# 2. Try HTML clipboard via RegisterClipboardFormatA("HTML Format").
# 3. Parse anchor href=... values from the HTML block.
# 4. Read CF_UNICODETEXT as before.
# 5. If URLs were found, build: "<text> (<url1, url2, ...>)"
# 6. Otherwise keep the old plain-text behavior.

shellcode_start:
  push ebp
  mov ebp, esp
  sub esp, 0x50
  push ebx
  push esi
  push edi

  call .Lget_base
.Lget_base:
  pop ebx
  mov eax, ebx
  .byte 0xBE
  .long RVA_GET_BASE
  sub eax, esi
  mov dword ptr [ebp-0x3C], eax

  mov dword ptr [ebp-0x04], ecx
  mov dword ptr [ebp-0x08], edx
  xor eax, eax
  mov dword ptr [ebp-0x0C], eax
  mov dword ptr [ebp-0x10], eax
  mov dword ptr [ebp-0x14], eax
  mov dword ptr [ebp-0x18], eax
  mov dword ptr [ebp-0x1C], eax
  mov dword ptr [ebp-0x20], eax
  mov dword ptr [ebp-0x38], eax
  mov dword ptr [ebp-0x34], eax
  mov dword ptr [ebp-0x30], eax
  mov dword ptr [ebp-0x2C], eax
  mov dword ptr [ebp-0x24], eax
  mov dword ptr [ebp-0x28], eax
  mov dword ptr [ebp-0x2C], eax
  mov dword ptr [ebp-0x30], eax
  mov dword ptr [ebp-0x34], eax
  mov dword ptr [ebp-0x38], eax
  mov dword ptr [ebp-0x40], eax
  mov dword ptr [ebp-0x44], eax
  mov dword ptr [ebp-0x48], eax
  mov dword ptr [ebp-0x4C], eax

  lea ecx, [ebp-0x0C]
  mov eax, dword ptr [ebp-0x3C]
  push dword ptr [eax + RVA_CLIP_OWNER]
  add eax, RVA_OPEN_CLIP_GUARD
  call eax
  test al, al
  je .Ldone

  xor eax, eax
  push eax
  push eax
  lea eax, [ebx + STR_USER32_OFF]
  push eax
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_LOADLIBEXA]
  test eax, eax
  je .Lread_plain

  mov esi, eax
  lea eax, [ebx + STR_REGFMT_OFF]
  push eax
  push esi
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GETPROCADDRESS]
  test eax, eax
  je .Lread_plain

  lea ecx, [ebx + STR_HTMLFMT_OFF]
  push ecx
  call eax
  test eax, eax
  je .Lread_plain

  push eax
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GETCLIPBOARDDATA]
  mov dword ptr [ebp-0x14], eax
  test eax, eax
  je .Lread_plain

  push eax
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GLOBALSIZE]
  mov dword ptr [ebp-0x38], eax
  test eax, eax
  je .Lread_plain

  push dword ptr [ebp-0x14]
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GLOBALLOCK]
  mov dword ptr [ebp-0x18], eax
  test eax, eax
  je .Lread_plain

  mov esi, dword ptr [ebp-0x18]
  mov ecx, dword ptr [ebp-0x38]
  call .Lfind_fragment_bounds
  test eax, eax
  je .Lread_plain

  mov esi, eax
  xor edi, edi
  call .Lscan_anchor_list
  mov dword ptr [ebp-0x40], eax
  mov dword ptr [ebp-0x44], ecx
  test eax, eax
  je .Lread_plain

  imul eax, eax, 12
  push eax
  push 0
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GLOBALALLOC]
  mov dword ptr [ebp-0x48], eax
  test eax, eax
  je .Lread_plain

  push eax
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GLOBALLOCK]
  mov dword ptr [ebp-0x4C], eax
  test eax, eax
  je .Lread_plain

  mov esi, dword ptr [ebp-0x18]
  mov ecx, dword ptr [ebp-0x38]
  call .Lfind_fragment_bounds
  test eax, eax
  je .Lread_plain

  mov esi, eax
  mov edi, dword ptr [ebp-0x4C]
  call .Lscan_anchor_list

.Lread_plain:
  push 0x0D
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GETCLIPBOARDDATA]
  mov dword ptr [ebp-0x1C], eax
  test eax, eax
  je .Lcleanup

  push eax
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GLOBALSIZE]
  dec eax
  sub eax, 1
  je .Lcleanup
  shr eax, 1

  mov ecx, dword ptr [ebp-0x08]
  test ecx, ecx
  je .Lgot_plain_len
  cmp ecx, eax
  cmovb eax, ecx

.Lgot_plain_len:
  mov dword ptr [ebp-0x24], eax
  push dword ptr [ebp-0x1C]
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GLOBALLOCK]
  mov dword ptr [ebp-0x20], eax
  test eax, eax
  je .Lcleanup

  mov edx, dword ptr [ebp-0x40]
  test edx, edx
  je .Lassign_plain
  cmp dword ptr [ebp-0x4C], 0
  je .Lassign_plain

  mov ecx, dword ptr [ebp-0x24]
  add ecx, dword ptr [ebp-0x44]
  lea eax, [edx+edx*2]
  add ecx, eax
  inc ecx
  mov dword ptr [ebp-0x34], ecx
  lea eax, [ecx*2]
  push eax
  push 0
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GLOBALALLOC]
  mov dword ptr [ebp-0x28], eax
  test eax, eax
  je .Lassign_plain

  mov edi, eax
  mov esi, dword ptr [ebp-0x20]
  mov ecx, dword ptr [ebp-0x24]
  mov ebx, dword ptr [ebp-0x4C]
  xor eax, eax
  mov dword ptr [ebp-0x2C], eax

.Lcopy_plain_loop:
  test ecx, ecx
  je .Lurl_done
  lodsw
  stosw
  inc dword ptr [ebp-0x2C]
  dec ecx

.Lcheck_inline_insert:
  cmp dword ptr [ebp-0x40], 0
  je .Lcopy_plain_loop
  mov eax, dword ptr [ebp-0x2C]
  cmp eax, dword ptr [ebx]
  jne .Lcopy_plain_loop
  mov dword ptr [ebp-0x50], esi
  mov dword ptr [ebp-0x30], ecx
  mov ax, 0x20
  stosw
  mov ax, 0x28
  stosw
  mov esi, dword ptr [ebx+4]
  mov ecx, dword ptr [ebx+8]
.Lurl_loop:
  test ecx, ecx
  je .Lurl_next
  lodsb
  xor ah, ah
  stosw
  dec ecx
  jmp .Lurl_loop

.Lurl_next:
  mov ax, 0x29
  stosw
  mov esi, dword ptr [ebp-0x50]
  mov ecx, dword ptr [ebp-0x30]
  add ebx, 12
  dec dword ptr [ebp-0x40]
  jmp .Lcheck_inline_insert

.Lurl_done:
  xor eax, eax
  stosw

  mov ecx, dword ptr [ebp-0x04]
  mov eax, dword ptr [ebp-0x34]
  dec eax
  push eax
  push dword ptr [ebp-0x28]
  mov eax, dword ptr [ebp-0x3C]
  add eax, RVA_ASSIGN_WIDE
  call eax
  mov dword ptr [ebp-0x10], 1
  jmp .Lcleanup

.Lassign_plain:
  mov ecx, dword ptr [ebp-0x04]
  push dword ptr [ebp-0x24]
  push dword ptr [ebp-0x20]
  mov eax, dword ptr [ebp-0x3C]
  add eax, RVA_ASSIGN_WIDE
  call eax
  mov dword ptr [ebp-0x10], 1

.Lcleanup:
  cmp dword ptr [ebp-0x28], 0
  je .Lskip_out_free
  push dword ptr [ebp-0x28]
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GLOBALFREE]

.Lskip_out_free:
  cmp dword ptr [ebp-0x4C], 0
  je .Lskip_meta_unlock
  push dword ptr [ebp-0x48]
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GLOBALUNLOCK]

.Lskip_meta_unlock:
  cmp dword ptr [ebp-0x48], 0
  je .Lskip_meta_free
  push dword ptr [ebp-0x48]
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GLOBALFREE]

.Lskip_meta_free:
  cmp dword ptr [ebp-0x20], 0
  je .Lskip_plain_unlock
  push dword ptr [ebp-0x1C]
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GLOBALUNLOCK]

.Lskip_plain_unlock:
  cmp dword ptr [ebp-0x18], 0
  je .Lskip_html_unlock
  push dword ptr [ebp-0x14]
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_GLOBALUNLOCK]

.Lskip_html_unlock:
  cmp byte ptr [ebp-0x0C], 0
  je .Ldone
  mov eax, dword ptr [ebp-0x3C]
  call dword ptr [eax + RVA_IAT_CLOSECLIPBOARD]

.Ldone:
  mov eax, dword ptr [ebp-0x10]
  pop edi
  pop esi
  pop ebx
  leave
  ret

# in:  esi = HTML buffer, ecx = buffer size
# out: eax = fragment start, edx = fragment end
.Lfind_fragment_bounds:
  push ebp
  mov ebp, esp
  sub esp, 8
  push edi

  lea eax, [esi+ecx]
  mov dword ptr [ebp-8], eax
  lea edi, [ebx + STR_STARTFRAG_OFF]
  mov edx, 20
  call .Lfind_bytes
  test eax, eax
  je .Lfrag_not_found
  add eax, 20
  mov dword ptr [ebp-4], eax

  mov esi, eax
  mov ecx, dword ptr [ebp-8]
  sub ecx, esi
  lea edi, [ebx + STR_ENDFRAG_OFF]
  mov edx, 18
  call .Lfind_bytes
  test eax, eax
  je .Lfrag_not_found

  mov edx, eax
  mov eax, dword ptr [ebp-4]
  pop edi
  leave
  ret

.Lfrag_not_found:
  xor eax, eax
  xor edx, edx
  pop edi
  leave
  ret

# in:  esi = haystack ptr, ecx = haystack len, edi = needle ptr, edx = needle len
# out: eax = found ptr or 0
.Lfind_bytes:
  test edx, edx
  je .Lfind_bytes_hit

.Lfind_bytes_loop:
  cmp ecx, edx
  jb .Lfind_bytes_miss
  push esi
  push edi
  mov eax, ecx
  mov ecx, edx
  repe cmpsb
  pop edi
  pop esi
  je .Lfind_bytes_hit
  mov ecx, eax
  inc esi
  dec ecx
  jmp .Lfind_bytes_loop

.Lfind_bytes_hit:
  mov eax, esi
  ret

.Lfind_bytes_miss:
  xor eax, eax
  ret

# in:  esi = fragment start, edx = fragment end, edi = metadata table or 0
# out: eax = anchor count, ecx = total URL length
.Lscan_anchor_list:
  push ebp
  mov ebp, esp
  sub esp, 0x24
  push ebx
  push esi
  push edi

  mov dword ptr [ebp-4], esi
  xor eax, eax
  mov dword ptr [ebp-8], eax
  mov dword ptr [ebp-0x0C], eax
  mov dword ptr [ebp-0x10], eax
  mov dword ptr [ebp-0x14], edx
  mov dword ptr [ebp-0x18], edi

.Lscan_anchor_loop:
  mov esi, dword ptr [ebp-4]
  mov ecx, dword ptr [ebp-0x14]
  sub ecx, esi
  jbe .Lscan_anchor_done
  call .Lfind_href
  test eax, eax
  je .Lscan_anchor_done
  mov dword ptr [ebp-0x1C], eax
  mov dword ptr [ebp-0x20], edx

  mov esi, eax
  mov edx, dword ptr [ebp-4]
  call .Lfind_prev_tag_start
  test eax, eax
  je .Lscan_anchor_done

  mov esi, dword ptr [ebp-4]
  mov edx, eax
  call .Lcount_visible
  add dword ptr [ebp-8], eax

  mov esi, dword ptr [ebp-0x1C]
  mov edx, dword ptr [ebp-0x14]
  call .Lfind_tag_end
  test eax, eax
  je .Lscan_anchor_done
  mov dword ptr [ebp-4], eax

  mov esi, eax
  mov edx, dword ptr [ebp-0x14]
  call .Lfind_close_anchor
  test eax, eax
  je .Lscan_anchor_done

  mov edx, eax
  mov dword ptr [ebp-0x24], eax
  mov esi, dword ptr [ebp-4]
  call .Lcount_visible
  add dword ptr [ebp-8], eax

  mov ecx, dword ptr [ebp-0x24]
  sub ecx, dword ptr [ebp-4]
  cmp ecx, dword ptr [ebp-0x20]
  jne .Lscan_anchor_store_metadata
  mov esi, dword ptr [ebp-4]
  mov edi, dword ptr [ebp-0x1C]
  cld
  repe cmpsb
  je .Lscan_anchor_skip_metadata

.Lscan_anchor_store_metadata:
  mov eax, dword ptr [ebp-0x18]
  test eax, eax
  je .Lscan_anchor_no_store
  mov ecx, dword ptr [ebp-8]
  mov dword ptr [eax], ecx
  mov ecx, dword ptr [ebp-0x1C]
  mov dword ptr [eax+4], ecx
  mov ecx, dword ptr [ebp-0x20]
  mov dword ptr [eax+8], ecx
  add dword ptr [ebp-0x18], 12

.Lscan_anchor_no_store:
  inc dword ptr [ebp-0x0C]
  mov eax, dword ptr [ebp-0x20]
  add dword ptr [ebp-0x10], eax

.Lscan_anchor_skip_metadata:
  mov esi, dword ptr [ebp-0x24]
  mov edx, dword ptr [ebp-0x14]
  call .Lfind_tag_end
  test eax, eax
  je .Lscan_anchor_done
  mov dword ptr [ebp-4], eax
  jmp .Lscan_anchor_loop

.Lscan_anchor_done:
  mov eax, dword ptr [ebp-0x0C]
  mov ecx, dword ptr [ebp-0x10]
  pop edi
  pop esi
  pop ebx
  leave
  ret

# in:  esi = pointer inside tag, edx = lower bound
# out: eax = nearest preceding '<' or 0
.Lfind_prev_tag_start:
  lea eax, [esi-1]
.Lfind_prev_tag_loop:
  cmp eax, edx
  jb .Lfind_prev_tag_miss
  cmp byte ptr [eax], '<'
  je .Lfind_prev_tag_hit
  dec eax
  jmp .Lfind_prev_tag_loop

.Lfind_prev_tag_hit:
  ret

.Lfind_prev_tag_miss:
  xor eax, eax
  ret

# in:  esi = search start, edx = upper bound
# out: eax = pointer after next '>' or 0
.Lfind_tag_end:
  mov eax, esi
.Lfind_tag_end_loop:
  cmp eax, edx
  jae .Lfind_tag_end_miss
  cmp byte ptr [eax], '>'
  je .Lfind_tag_end_hit
  inc eax
  jmp .Lfind_tag_end_loop

.Lfind_tag_end_hit:
  inc eax
  ret

.Lfind_tag_end_miss:
  xor eax, eax
  ret

# in:  esi = search start, edx = upper bound
# out: eax = pointer to '<' of closing </a ...> or 0
.Lfind_close_anchor:
  mov eax, esi
.Lfind_close_anchor_loop:
  cmp eax, edx
  jae .Lfind_close_anchor_miss
  lea ecx, [eax+3]
  cmp ecx, edx
  ja .Lfind_close_anchor_miss
  cmp byte ptr [eax], '<'
  jne .Lfind_close_anchor_next
  cmp byte ptr [eax+1], '/'
  jne .Lfind_close_anchor_next
  mov cl, byte ptr [eax+2]
  or cl, 0x20
  cmp cl, 'a'
  jne .Lfind_close_anchor_next
  mov cl, byte ptr [eax+3]
  cmp cl, '>'
  je .Lfind_close_anchor_hit
  cmp cl, ' '
  je .Lfind_close_anchor_hit
  cmp cl, 9
  je .Lfind_close_anchor_hit
  cmp cl, 0x0D
  je .Lfind_close_anchor_hit
  cmp cl, 0x0A
  je .Lfind_close_anchor_hit

.Lfind_close_anchor_next:
  inc eax
  jmp .Lfind_close_anchor_loop

.Lfind_close_anchor_hit:
  ret

.Lfind_close_anchor_miss:
  xor eax, eax
  ret

# in:  esi = start, edx = end
# out: eax = visible UTF-8 codepoint count ignoring tags/comments
.Lcount_visible:
  push ebx
  xor eax, eax

.Lcount_visible_loop:
  cmp esi, edx
  jae .Lcount_visible_done
  mov bl, byte ptr [esi]
  cmp bl, '<'
  je .Lcount_visible_tag
  cmp bl, '&'
  je .Lcount_visible_entity
  cmp bl, 0x80
  jb .Lcount_visible_one
  mov bh, bl
  and bh, 0xE0
  cmp bh, 0xC0
  jne .Lcount_visible_check3
  lea ecx, [esi+2]
  cmp ecx, edx
  ja .Lcount_visible_one
  add esi, 2
  inc eax
  jmp .Lcount_visible_loop

.Lcount_visible_check3:
  mov bh, bl
  and bh, 0xF0
  cmp bh, 0xE0
  jne .Lcount_visible_check4
  lea ecx, [esi+3]
  cmp ecx, edx
  ja .Lcount_visible_one
  add esi, 3
  inc eax
  jmp .Lcount_visible_loop

.Lcount_visible_check4:
  mov bh, bl
  and bh, 0xF8
  cmp bh, 0xF0
  jne .Lcount_visible_one
  lea ecx, [esi+4]
  cmp ecx, edx
  ja .Lcount_visible_one
  add esi, 4
  add eax, 2
  jmp .Lcount_visible_loop

.Lcount_visible_entity:
  push eax
  call .Ldecode_entity_units
  mov ecx, eax
  pop eax
  test ecx, ecx
  je .Lcount_visible_one
  add esi, ecx
  add eax, ebx
  jmp .Lcount_visible_loop

.Lcount_visible_one:
  inc esi
  inc eax
  jmp .Lcount_visible_loop

.Lcount_visible_tag:
  lea ecx, [esi+4]
  cmp ecx, edx
  ja .Lcount_visible_skip_tag
  cmp byte ptr [esi+1], '!'
  jne .Lcount_visible_skip_tag
  cmp byte ptr [esi+2], '-'
  jne .Lcount_visible_skip_tag
  cmp byte ptr [esi+3], '-'
  jne .Lcount_visible_skip_tag
  add esi, 4
.Lcount_visible_comment_loop:
  lea ecx, [esi+2]
  cmp ecx, edx
  jae .Lcount_visible_done
  cmp byte ptr [esi], '-'
  jne .Lcount_visible_comment_next
  cmp byte ptr [esi+1], '-'
  jne .Lcount_visible_comment_next
  cmp byte ptr [esi+2], '>'
  jne .Lcount_visible_comment_next
  add esi, 3
  jmp .Lcount_visible_loop

.Lcount_visible_comment_next:
  inc esi
  jmp .Lcount_visible_comment_loop

.Lcount_visible_skip_tag:
  mov ecx, eax
  call .Lfind_tag_end
  test eax, eax
  je .Lcount_visible_tag_fail
  mov esi, eax
  mov eax, ecx
  jmp .Lcount_visible_loop

.Lcount_visible_tag_fail:
  mov eax, ecx

.Lcount_visible_done:
  pop ebx
  ret

# in:  esi = current '&', edx = end
# out: eax = bytes consumed including ';' or 0, ebx = UTF-16 code units (1 or 2)
.Ldecode_entity_units:
  push ecx
  push edi
  xor eax, eax
  xor ebx, ebx

  cmp byte ptr [esi], '&'
  jne .Lentity_miss
  lea edi, [esi+1]
  cmp edi, edx
  jae .Lentity_miss
  mov cl, byte ptr [edi]
  cmp cl, '#'
  je .Lentity_numeric

  mov eax, edi
.Lentity_named_loop:
  cmp edi, edx
  jae .Lentity_miss
  mov cl, byte ptr [edi]
  cmp cl, ';'
  je .Lentity_named_done
  cmp cl, '0'
  jb .Lentity_named_alpha
  cmp cl, '9'
  jbe .Lentity_named_next

.Lentity_named_alpha:
  or cl, 0x20
  cmp cl, 'a'
  jb .Lentity_miss
  cmp cl, 'z'
  ja .Lentity_miss

.Lentity_named_next:
  inc edi
  jmp .Lentity_named_loop

.Lentity_named_done:
  cmp edi, eax
  je .Lentity_miss
  mov eax, edi
  sub eax, esi
  inc eax
  mov ebx, 1
  jmp .Lentity_done

.Lentity_numeric:
  inc edi
  cmp edi, edx
  jae .Lentity_miss
  xor ebx, ebx
  xor eax, eax
  mov cl, byte ptr [edi]
  cmp cl, 'x'
  je .Lentity_hex_start
  cmp cl, 'X'
  je .Lentity_hex_start
  jmp .Lentity_dec_loop

.Lentity_hex_start:
  inc edi
  cmp edi, edx
  jae .Lentity_miss

.Lentity_hex_loop:
  cmp edi, edx
  jae .Lentity_miss
  mov cl, byte ptr [edi]
  cmp cl, ';'
  je .Lentity_scalar_done
  cmp cl, '0'
  jb .Lentity_hex_alpha
  cmp cl, '9'
  jbe .Lentity_hex_digit

.Lentity_hex_alpha:
  or cl, 0x20
  cmp cl, 'a'
  jb .Lentity_miss
  cmp cl, 'f'
  ja .Lentity_miss
  sub cl, 'a'
  add cl, 10
  jmp .Lentity_hex_apply

.Lentity_hex_digit:
  sub cl, '0'

.Lentity_hex_apply:
  shl ebx, 4
  movzx ecx, cl
  add ebx, ecx
  inc eax
  inc edi
  jmp .Lentity_hex_loop

.Lentity_dec_loop:
  cmp edi, edx
  jae .Lentity_miss
  mov cl, byte ptr [edi]
  cmp cl, ';'
  je .Lentity_scalar_done
  cmp cl, '0'
  jb .Lentity_miss
  cmp cl, '9'
  ja .Lentity_miss
  imul ebx, ebx, 10
  sub cl, '0'
  movzx ecx, cl
  add ebx, ecx
  inc eax
  inc edi
  jmp .Lentity_dec_loop

.Lentity_scalar_done:
  test eax, eax
  je .Lentity_miss
  cmp ebx, 0x10FFFF
  ja .Lentity_miss
  mov eax, edi
  sub eax, esi
  inc eax
  cmp ebx, 0x10000
  jb .Lentity_one_unit
  mov ebx, 2
  jmp .Lentity_done

.Lentity_one_unit:
  mov ebx, 1
  jmp .Lentity_done

.Lentity_miss:
  xor eax, eax
  xor ebx, ebx

.Lentity_done:
  pop edi
  pop ecx
  ret

# in:  esi = HTML buffer, ecx = buffer size
# out: eax = URL start or 0, edx = URL length
.Lfind_href:
  push ebx
  push edi
  mov edi, esi

.Lscan_next:
  cmp ecx, 3
  jb .Lhref_not_found

  mov al, byte ptr [edi]
  cmp al, '<'
  jne .Lhref_advance
  mov al, byte ptr [edi]
  mov al, byte ptr [edi+1]
  or al, 0x20
  cmp al, 'a'
  jne .Lhref_advance
  mov al, byte ptr [edi+2]
  cmp al, '>'
  je .Lhref_advance
  cmp al, ' '
  je .Lanchor_attrs
  cmp al, 9
  je .Lanchor_attrs
  cmp al, 0x0D
  je .Lanchor_attrs
  cmp al, 0x0A
  je .Lanchor_attrs
  jmp .Lhref_advance

.Lanchor_attrs:
  lea eax, [edi+2]
  mov edx, ecx
  sub edx, 2

.Lattr_scan:
  cmp edx, 1
  jb .Lhref_advance
  mov bl, byte ptr [eax]
  cmp bl, '>'
  je .Lhref_advance
  cmp bl, ' '
  je .Lattr_scan_consume
  cmp bl, 9
  je .Lattr_scan_consume
  cmp bl, 0x0D
  je .Lattr_scan_consume
  cmp bl, 0x0A
  je .Lattr_scan_consume
  cmp edx, 5
  jb .Lhref_advance
  mov bl, byte ptr [eax]
  or bl, 0x20
  cmp bl, 'h'
  jne .Lattr_scan_consume
  mov bl, byte ptr [eax+1]
  or bl, 0x20
  cmp bl, 'r'
  jne .Lattr_scan_consume
  mov bl, byte ptr [eax+2]
  or bl, 0x20
  cmp bl, 'e'
  jne .Lattr_scan_consume
  mov bl, byte ptr [eax+3]
  or bl, 0x20
  cmp bl, 'f'
  jne .Lattr_scan_consume

  lea eax, [eax+4]
  sub edx, 4

.Lskip_pre_eq:
  cmp edx, 1
  jb .Lhref_advance
  mov bl, byte ptr [eax]
  cmp bl, ' '
  je .Lskip_pre_eq_consume
  cmp bl, 9
  je .Lskip_pre_eq_consume
  cmp bl, 0x0D
  je .Lskip_pre_eq_consume
  cmp bl, 0x0A
  je .Lskip_pre_eq_consume
  cmp bl, '='
  jne .Lattr_scan_consume
  inc eax
  dec edx
  jmp .Lskip_post_eq

.Lskip_pre_eq_consume:
  inc eax
  dec edx
  jmp .Lskip_pre_eq

.Lskip_post_eq:
  cmp edx, 1
  jb .Lhref_advance
  mov bl, byte ptr [eax]
  cmp bl, ' '
  je .Lskip_post_eq_consume
  cmp bl, 9
  je .Lskip_post_eq_consume
  cmp bl, 0x0D
  je .Lskip_post_eq_consume
  cmp bl, 0x0A
  je .Lskip_post_eq_consume
  cmp bl, '"'
  je .Ldouble_quoted
  cmp bl, 39
  je .Lsingle_quoted
  jmp .Lunquoted

.Lskip_post_eq_consume:
  inc eax
  dec edx
  jmp .Lskip_post_eq

.Lattr_scan_consume:
  inc eax
  dec edx
  jmp .Lattr_scan

.Ldouble_quoted:
  inc eax
  dec edx
  mov esi, eax
  xor ecx, ecx
.Ldouble_loop:
  cmp ecx, edx
  jae .Lhref_not_found
  mov al, byte ptr [esi+ecx]
  cmp al, '"'
  je .Lhref_found
  inc ecx
  jmp .Ldouble_loop

.Lsingle_quoted:
  inc eax
  dec edx
  mov esi, eax
  xor ecx, ecx
.Lsingle_loop:
  cmp ecx, edx
  jae .Lhref_advance
  mov al, byte ptr [esi+ecx]
  cmp al, 39
  je .Lhref_found
  inc ecx
  jmp .Lsingle_loop

.Lunquoted:
  mov esi, eax
  xor ecx, ecx
.Lunquoted_loop:
  cmp ecx, edx
  jae .Lhref_found
  mov al, byte ptr [esi+ecx]
  test al, al
  je .Lhref_found
  cmp al, ' '
  je .Lhref_found
  cmp al, 9
  je .Lhref_found
  cmp al, '>'
  je .Lhref_found
  inc ecx
  jmp .Lunquoted_loop

.Lhref_found:
  mov eax, esi
  mov edx, ecx
  pop edi
  pop ebx
  ret

.Lhref_advance:
  inc edi
  dec ecx
  jmp .Lscan_next

.Lhref_not_found:
  xor eax, eax
  xor edx, edx
  pop edi
  pop ebx
  ret

.balign 4
.Lstr_user32:
  .asciz "user32.dll"
.Lstr_regfmt:
  .asciz "RegisterClipboardFormatA"
.Lstr_htmlfmt:
  .asciz "HTML Format"
.Lstr_startfrag:
  .ascii "<!--StartFragment-->"
.Lstr_endfrag:
  .ascii "<!--EndFragment-->"
.Lstr_http:
  .ascii "http://"
.Lstr_https:
  .ascii "https://"
.Lstr_ftp:
  .ascii "ftp://"
.Lstr_file:
  .ascii "file://"
.Lstr_mailto:
  .ascii "mailto:"
.balign 4
.Lguid_clsid_cuiautomation:
  .byte 0xA4, 0xDB, 0x48, 0xFF, 0xEF, 0x60, 0x01, 0x42
  .byte 0xAA, 0x87, 0x54, 0x10, 0x3E, 0xEF, 0x59, 0x4E
.Lguid_iid_iuiautomation:
  .byte 0x7D, 0xE5, 0xCB, 0x30, 0xD0, 0xD9, 0x2A, 0x45
  .byte 0xAB, 0x13, 0x7A, 0xC5, 0xAC, 0x48, 0x25, 0xEE
.Lguid_iid_iuiautomationvaluepattern:
  .byte 0xB1, 0xD8, 0x4C, 0xA9, 0x44, 0x08, 0xD6, 0x4C
  .byte 0x9D, 0x2D, 0x64, 0x05, 0x37, 0xAB, 0x39, 0xE9

# Replacement for 0x404901 (stdcall):
#   stack arg = output string object
#
# Strategy:
# 1. Use AccessibleObjectFromPoint like the original routine.
# 2. Read both accName and accValue.
# 3. Keep old behavior unless accValue looks like a URL.
# 4. If both are useful, build "<name> (<url>)".

.balign 4
accessibility_shellcode_delegate_start:
  push ebp
  mov ebp, esp
  push ebx
  call .Lacc_delegate_get_base
.Lacc_delegate_get_base:
  pop eax
  .byte 0xBA
  .long CAVE_RVA + .Lacc_delegate_get_base - shellcode_start
  sub eax, edx
  push dword ptr [ebp+0x08]
  add eax, RVA_ORIGINAL_ACCESSIBILITY
  call eax
  pop ebx
  leave
  ret 4

.balign 4
accessibility_shellcode_noop_start:
  push ebp
  mov ebp, esp
  push ebx
  mov ebx, dword ptr [ebp+0x08]
  mov ecx, ebx
  call .Lacc_noop_get_base
.Lacc_noop_get_base:
  pop eax
  .byte 0xBA
  .long CAVE_RVA + .Lacc_noop_get_base - shellcode_start
  sub eax, edx
  add eax, RVA_CLEAR_WIDE
  call eax
  xor eax, eax
  pop ebx
  leave
  ret 4

.balign 4
accessibility_shellcode_name_only_start:
  push ebp
  mov ebp, esp
  push ebx
  call .Lacc_name_get_base
.Lacc_name_get_base:
  pop eax
  .byte 0xBA
  .long CAVE_RVA + .Lacc_name_get_base - shellcode_start
  sub eax, edx
  push dword ptr [ebp+0x08]
  add eax, RVA_ORIGINAL_ACCESSIBILITY
  call eax
  pop ebx
  leave
  ret 4

.balign 4
accessibility_shellcode_uia_point_start:
  push ebp
  mov ebp, esp
  sub esp, 0x50
  push ebx
  push esi
  push edi
  cld

  call .Lacc_uia_get_base
.Lacc_uia_get_base:
  pop ebx
  mov eax, ebx
  .byte 0xBE
  .long CAVE_RVA + .Lacc_uia_get_base - shellcode_start
  sub eax, esi
  mov dword ptr [ebp-0x04], eax
  lea edx, [ebx + ACC_UIA_DATA_BASE_DELTA]
  mov dword ptr [ebp-0x4C], edx

  xor eax, eax
  mov dword ptr [ebp-0x08], eax
  mov dword ptr [ebp-0x0C], eax
  mov dword ptr [ebp-0x10], eax
  mov dword ptr [ebp-0x14], eax
  mov dword ptr [ebp-0x18], eax
  mov dword ptr [ebp-0x1C], eax
  mov dword ptr [ebp-0x20], eax
  mov dword ptr [ebp-0x24], eax
  mov dword ptr [ebp-0x28], eax
  mov dword ptr [ebp-0x2C], eax
  mov dword ptr [ebp-0x30], eax
  mov dword ptr [ebp-0x34], eax
  mov dword ptr [ebp-0x38], eax
  mov dword ptr [ebp-0x3C], eax
  mov dword ptr [ebp-0x40], eax

  lea eax, [ebp-0x40]
  push eax
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_GETCURSORPOS]
  test eax, eax
  je .Lacc_uia_cleanup

  push 0x2
  push 0
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_COINITIALIZEEX]
  mov dword ptr [ebp-0x08], eax
  cmp eax, 0x80010106
  je .Lacc_uia_co_ready
  test eax, eax
  js .Lacc_uia_cleanup

.Lacc_uia_co_ready:
  lea eax, [ebp-0x0C]
  push eax
  mov edx, dword ptr [ebp-0x4C]
  lea eax, [edx + GUID_IUIAUTOMATION_OFF_ACC]
  push eax
  push 0x1
  push 0
  mov edx, dword ptr [ebp-0x4C]
  lea eax, [edx + GUID_CUIAUTOMATION_OFF_ACC]
  push eax
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_COCREATEINSTANCE]
  test eax, eax
  js .Lacc_uia_cleanup
  cmp dword ptr [ebp-0x0C], 0
  je .Lacc_uia_cleanup

  mov ecx, dword ptr [ebp-0x0C]
  mov eax, dword ptr [ecx]
  lea edi, [ebp-0x10]
  push edi
  push dword ptr [ebp-0x3C]
  push dword ptr [ebp-0x40]
  push ecx
  call dword ptr [eax+0x1C]
  test eax, eax
  js .Lacc_uia_cleanup
  cmp dword ptr [ebp-0x10], 0
  je .Lacc_uia_cleanup

  mov ecx, dword ptr [ebp-0x10]
  mov eax, dword ptr [ecx]
  lea edx, [ebp-0x28]
  push edx
  push ecx
  call dword ptr [eax+0x54]
  test eax, eax
  js .Lacc_uia_cleanup
  cmp dword ptr [ebp-0x28], 50005
  jne .Lacc_uia_cleanup

  mov ecx, dword ptr [ebp-0x10]
  mov eax, dword ptr [ecx]
  lea edx, [ebp-0x18]
  push edx
  push ecx
  call dword ptr [eax+0x5C]
  test eax, eax
  js .Lacc_uia_cleanup
  push dword ptr [ebp-0x18]
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_SYSSTRINGLEN]
  mov dword ptr [ebp-0x2C], eax
  test eax, eax
  je .Lacc_uia_cleanup

  mov ecx, dword ptr [ebp-0x10]
  mov eax, dword ptr [ecx]
  lea edx, [ebp-0x14]
  push edx
  mov edx, dword ptr [ebp-0x4C]
  lea edx, [edx + GUID_IUIAUTOMATIONVALUEPATTERN_OFF_ACC]
  push edx
  push 0x2712
  push ecx
  call dword ptr [eax+0x38]
  test eax, eax
  js .Lacc_uia_cleanup
  cmp dword ptr [ebp-0x14], 0
  je .Lacc_uia_cleanup

  mov ecx, dword ptr [ebp-0x14]
  mov eax, dword ptr [ecx]
  lea edx, [ebp-0x1C]
  push edx
  push ecx
  call dword ptr [eax+0x10]
  test eax, eax
  js .Lacc_uia_cleanup
  push dword ptr [ebp-0x1C]
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_SYSSTRINGLEN]
  mov dword ptr [ebp-0x30], eax
  test eax, eax
  je .Lacc_uia_cleanup

  mov esi, dword ptr [ebp-0x1C]
  mov ecx, dword ptr [ebp-0x30]
  push ebx
  mov ebx, dword ptr [ebp-0x4C]
  call .Lis_url_like_wide
  pop ebx
  test al, al
  je .Lacc_uia_cleanup

  mov eax, dword ptr [ebp-0x2C]
  add eax, dword ptr [ebp-0x30]
  add eax, 3
  mov dword ptr [ebp-0x38], eax
  lea eax, [eax*2 + 2]
  push eax
  push 0
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_GLOBALALLOC]
  mov dword ptr [ebp-0x20], eax
  test eax, eax
  je .Lacc_uia_cleanup

  mov edi, eax
  mov esi, dword ptr [ebp-0x18]
  mov ecx, dword ptr [ebp-0x2C]
  rep movsw
  mov ax, 0x20
  stosw
  mov ax, 0x28
  stosw
  mov esi, dword ptr [ebp-0x1C]
  mov ecx, dword ptr [ebp-0x30]
  rep movsw
  mov ax, 0x29
  stosw
  xor eax, eax
  stosw

  mov ecx, dword ptr [ebp+0x08]
  push dword ptr [ebp-0x38]
  push dword ptr [ebp-0x20]
  mov eax, dword ptr [ebp-0x04]
  add eax, RVA_ASSIGN_WIDE
  call eax
  mov dword ptr [ebp-0x24], 1

.Lacc_uia_cleanup:
  cmp dword ptr [ebp-0x20], 0
  je .Lacc_uia_skip_tmp_free
  push dword ptr [ebp-0x20]
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_GLOBALFREE]

.Lacc_uia_skip_tmp_free:
  cmp dword ptr [ebp-0x1C], 0
  je .Lacc_uia_skip_value_free
  push dword ptr [ebp-0x1C]
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_SYSFREESTRING]

.Lacc_uia_skip_value_free:
  cmp dword ptr [ebp-0x18], 0
  je .Lacc_uia_skip_name_free
  push dword ptr [ebp-0x18]
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_SYSFREESTRING]

.Lacc_uia_skip_name_free:
  cmp dword ptr [ebp-0x14], 0
  je .Lacc_uia_skip_valuepattern_release
  mov ecx, dword ptr [ebp-0x14]
  mov edx, dword ptr [ecx]
  push ecx
  call dword ptr [edx+0x08]

.Lacc_uia_skip_valuepattern_release:
  cmp dword ptr [ebp-0x10], 0
  je .Lacc_uia_skip_element_release
  mov ecx, dword ptr [ebp-0x10]
  mov edx, dword ptr [ecx]
  push ecx
  call dword ptr [edx+0x08]

.Lacc_uia_skip_element_release:
  cmp dword ptr [ebp-0x0C], 0
  je .Lacc_uia_skip_automation_release
  mov ecx, dword ptr [ebp-0x0C]
  mov edx, dword ptr [ecx]
  push ecx
  call dword ptr [edx+0x08]

.Lacc_uia_skip_automation_release:
  cmp dword ptr [ebp-0x24], 0
  jne .Lacc_uia_after_fallback

  mov eax, dword ptr [ebp-0x04]
  push dword ptr [ebp+0x08]
  add eax, RVA_ORIGINAL_ACCESSIBILITY
  call eax
  mov dword ptr [ebp-0x24], eax

.Lacc_uia_after_fallback:
  cmp dword ptr [ebp-0x08], 0
  je .Lacc_uia_call_couninit
  cmp dword ptr [ebp-0x08], 1
  je .Lacc_uia_call_couninit
  jmp .Lacc_uia_done

.Lacc_uia_call_couninit:
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_COUNINITIALIZE]

.Lacc_uia_done:
  mov eax, dword ptr [ebp-0x24]
  pop edi
  pop esi
  pop ebx
  leave
  ret 4

.balign 4
accessibility_shellcode_start:
  push ebp
  mov ebp, esp
  sub esp, 0x50
  push ebx
  push esi
  push edi
  cld

  call .Lacc_get_base
.Lacc_get_base:
  pop ebx
  mov eax, ebx
  .byte 0xBE
  .long RVA_ACC_GET_BASE
  sub eax, esi
  mov dword ptr [ebp-0x04], eax

  mov edi, dword ptr [ebp+0x08]
  mov ecx, edi
  add eax, RVA_CLEAR_WIDE
  call eax

  xor eax, eax
  mov dword ptr [ebp-0x08], eax
  mov dword ptr [ebp-0x0C], eax
  mov dword ptr [ebp-0x10], eax
  mov dword ptr [ebp-0x14], eax
  mov dword ptr [ebp-0x18], eax
  mov dword ptr [ebp-0x1C], eax
  mov dword ptr [ebp-0x20], eax
  mov dword ptr [ebp-0x48], eax
  mov dword ptr [ebp-0x44], eax
  mov dword ptr [ebp-0x40], eax
  mov dword ptr [ebp-0x3C], eax

  mov eax, dword ptr [ebp-0x04]
  cmp byte ptr [eax + RVA_ACC_READY_FLAG], 0
  je .Lacc_cleanup

  lea eax, [ebp-0x28]
  push eax
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_GETCURSORPOS]
  test eax, eax
  je .Lacc_cleanup

  lea eax, [ebp-0x38]
  push eax
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_VARIANTINIT]
  lea eax, [ebp-0x48]
  push eax
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_VARIANTINIT]

  lea eax, [ebp-0x38]
  push eax
  lea eax, [ebp-0x08]
  push eax
  push dword ptr [ebp-0x24]
  push dword ptr [ebp-0x28]
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_ACCESSIBLEOBJECTFROMPOINT]
  test eax, eax
  js .Lacc_cleanup

  mov eax, dword ptr [ebp-0x08]
  test eax, eax
  je .Lacc_cleanup

  lea edx, [ebp-0x0C]
  push edx
  sub esp, 0x10
  mov ecx, dword ptr [eax]
  lea esi, [ebp-0x38]
  mov edi, esp
  push eax
  movsd
  movsd
  movsd
  movsd
  call dword ptr [ecx+0x28]

  push dword ptr [ebp-0x0C]
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_SYSSTRINGLEN]
  mov dword ptr [ebp-0x14], eax

.Lacc_maybe_read_value:
  cmp dword ptr [ebp-0x14], 0
  je .Lacc_read_value

  mov eax, dword ptr [ebp-0x08]
  lea edx, [ebp-0x48]
  push edx
  sub esp, 0x10
  mov ecx, dword ptr [eax]
  lea esi, [ebp-0x38]
  mov edi, esp
  push eax
  movsd
  movsd
  movsd
  movsd
  call dword ptr [ecx+0x34]
  test eax, eax
  js .Lacc_assign_name
  cmp word ptr [ebp-0x48], 3
  je .Lacc_role_dword
  cmp word ptr [ebp-0x48], 2
  jne .Lacc_assign_name
  cmp word ptr [ebp-0x40], 0x1E
  jne .Lacc_assign_name
  jmp .Lacc_read_value

.Lacc_role_dword:
  cmp dword ptr [ebp-0x40], 0x1E
  jne .Lacc_assign_name

.Lacc_read_value:
  mov eax, dword ptr [ebp-0x08]
  lea edx, [ebp-0x10]
  push edx
  sub esp, 0x10
  mov ecx, dword ptr [eax]
  lea esi, [ebp-0x38]
  mov edi, esp
  push eax
  movsd
  movsd
  movsd
  movsd
  call dword ptr [ecx+0x2C]

  push dword ptr [ebp-0x10]
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_SYSSTRINGLEN]
  mov dword ptr [ebp-0x18], eax

  cmp dword ptr [ebp-0x14], 0
  je .Lacc_try_value_only
  cmp dword ptr [ebp-0x18], 0
  je .Lacc_assign_name

  mov eax, dword ptr [ebp-0x14]
  cmp eax, dword ptr [ebp-0x18]
  jne .Lacc_check_url
  mov esi, dword ptr [ebp-0x0C]
  mov edi, dword ptr [ebp-0x10]
  mov ecx, dword ptr [ebp-0x14]
  call .Lwide_equal
  test al, al
  jne .Lacc_assign_name

.Lacc_check_url:
  mov esi, dword ptr [ebp-0x10]
  mov ecx, dword ptr [ebp-0x18]
  call .Lis_url_like_wide
  test al, al
  je .Lacc_assign_name

  mov eax, dword ptr [ebp-0x14]
  add eax, dword ptr [ebp-0x18]
  add eax, 3
  mov dword ptr [ebp-0x20], eax
  lea eax, [eax*2 + 2]
  push eax
  push 0
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_GLOBALALLOC]
  mov dword ptr [ebp-0x1C], eax
  test eax, eax
  je .Lacc_assign_name

  mov edi, eax
  mov esi, dword ptr [ebp-0x0C]
  mov ecx, dword ptr [ebp-0x14]
  rep movsw
  mov ax, 0x20
  stosw
  mov ax, 0x28
  stosw
  mov esi, dword ptr [ebp-0x10]
  mov ecx, dword ptr [ebp-0x18]
  rep movsw
  mov ax, 0x29
  stosw
  xor eax, eax
  stosw

  mov ecx, dword ptr [ebp+0x08]
  push dword ptr [ebp-0x20]
  push dword ptr [ebp-0x1C]
  mov eax, dword ptr [ebp-0x04]
  add eax, RVA_ASSIGN_WIDE
  call eax
  mov dword ptr [ebp-0x20], 1
  jmp .Lacc_cleanup

.Lacc_try_value_only:
  cmp dword ptr [ebp-0x18], 0
  je .Lacc_cleanup
  mov ecx, dword ptr [ebp+0x08]
  push dword ptr [ebp-0x18]
  push dword ptr [ebp-0x10]
  mov eax, dword ptr [ebp-0x04]
  add eax, RVA_ASSIGN_WIDE
  call eax
  mov dword ptr [ebp-0x20], 1
  jmp .Lacc_cleanup

.Lacc_assign_name:
  mov ecx, dword ptr [ebp+0x08]
  push dword ptr [ebp-0x14]
  push dword ptr [ebp-0x0C]
  mov eax, dword ptr [ebp-0x04]
  add eax, RVA_ASSIGN_WIDE
  call eax
  mov dword ptr [ebp-0x20], 1

.Lacc_cleanup:
  cmp dword ptr [ebp-0x1C], 0
  je .Lacc_skip_tmp_free
  push dword ptr [ebp-0x1C]
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_GLOBALFREE]

.Lacc_skip_tmp_free:
  cmp dword ptr [ebp-0x10], 0
  je .Lacc_skip_value_free
  push dword ptr [ebp-0x10]
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_SYSFREESTRING]

.Lacc_skip_value_free:
  cmp dword ptr [ebp-0x0C], 0
  je .Lacc_skip_name_free
  push dword ptr [ebp-0x0C]
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_SYSFREESTRING]

.Lacc_skip_name_free:
  lea eax, [ebp-0x48]
  push eax
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_VARIANTCLEAR]

  lea eax, [ebp-0x38]
  push eax
  mov eax, dword ptr [ebp-0x04]
  call dword ptr [eax + RVA_IAT_VARIANTCLEAR]

  mov ecx, dword ptr [ebp-0x08]
  test ecx, ecx
  je .Lacc_done
  mov edx, dword ptr [ecx]
  push ecx
  call dword ptr [edx+0x08]

.Lacc_done:
  mov eax, dword ptr [ebp-0x20]
  pop edi
  pop esi
  pop ebx
  leave
  ret 4

# in:  esi = wide string, ecx = UTF-16 length
# out: al = 1 if it looks like a URL or mailto
.Lis_url_like_wide:
  push ebx
  push edi
  push edx

  lea edi, [ebx + STR_HTTPS_OFF_ACC]
  mov edx, 8
  call .Lmatch_prefix_wide_ci
  test al, al
  jne .Lurl_like_yes

  lea edi, [ebx + STR_HTTP_OFF_ACC]
  mov edx, 7
  call .Lmatch_prefix_wide_ci
  test al, al
  jne .Lurl_like_yes

  lea edi, [ebx + STR_FTP_OFF_ACC]
  mov edx, 6
  call .Lmatch_prefix_wide_ci
  test al, al
  jne .Lurl_like_yes

  lea edi, [ebx + STR_FILE_OFF_ACC]
  mov edx, 7
  call .Lmatch_prefix_wide_ci
  test al, al
  jne .Lurl_like_yes

  lea edi, [ebx + STR_MAILTO_OFF_ACC]
  mov edx, 7
  call .Lmatch_prefix_wide_ci
  test al, al
  jne .Lurl_like_yes

  xor eax, eax
  jmp .Lurl_like_done

.Lurl_like_yes:
  mov al, 1

.Lurl_like_done:
  pop edx
  pop edi
  pop ebx
  ret

# in:  esi = wide string, ecx = UTF-16 length, edi = ascii prefix, edx = prefix len
# out: al = 1 on match
.Lmatch_prefix_wide_ci:
  push ebx
  push esi
  push edi
  push ecx
  push edx
  xor eax, eax
  cmp ecx, edx
  jb .Lmatch_prefix_done

.Lmatch_prefix_loop:
  test edx, edx
  je .Lmatch_prefix_yes
  mov ax, word ptr [esi]
  test ah, ah
  jne .Lmatch_prefix_done
  cmp al, 'A'
  jb .Lmatch_prefix_lower
  cmp al, 'Z'
  ja .Lmatch_prefix_lower
  or al, 0x20

.Lmatch_prefix_lower:
  mov bl, byte ptr [edi]
  cmp bl, 'A'
  jb .Lmatch_prefix_cmp
  cmp bl, 'Z'
  ja .Lmatch_prefix_cmp
  or bl, 0x20

.Lmatch_prefix_cmp:
  cmp al, bl
  jne .Lmatch_prefix_done
  add esi, 2
  inc edi
  dec edx
  jmp .Lmatch_prefix_loop

.Lmatch_prefix_yes:
  mov al, 1

.Lmatch_prefix_done:
  pop edx
  pop ecx
  pop edi
  pop esi
  pop ebx
  ret

# in:  esi = first wide string, edi = second wide string, ecx = UTF-16 length
# out: al = 1 on exact match
.Lwide_equal:
  push esi
  push edi
  xor eax, eax
  repe cmpsw
  sete al
  pop edi
  pop esi
  ret
