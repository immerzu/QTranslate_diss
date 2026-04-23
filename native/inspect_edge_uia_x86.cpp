#define COBJMACROS
#define _CRT_SECURE_NO_WARNINGS

#include <windows.h>
#include <ole2.h>
#include <stdio.h>
#include <wchar.h>
#include <UIAutomation.h>

namespace {

constexpr wchar_t kProbeTitle[] = L"Codex Browser UIA Native Probe";
constexpr wchar_t kLinkUrl[] = L"https://browser.example/test-link";
constexpr char kHtmlTemplate[] =
    "<!doctype html>\n"
    "<html>\n"
    "<head>\n"
    "  <meta charset=\"utf-8\">\n"
    "  <title>Codex Browser UIA Native Probe</title>\n"
    "  <style>\n"
    "    html, body {\n"
    "      margin: 0;\n"
    "      padding: 0;\n"
    "      background: #f5f1e8;\n"
    "      font-family: Georgia, 'Times New Roman', serif;\n"
    "    }\n"
    "    .wrap {\n"
    "      padding: 56px;\n"
    "    }\n"
    "    a.probe {\n"
    "      display: inline-block;\n"
    "      font-size: 48px;\n"
    "      line-height: 1.2;\n"
    "      color: #0d47a1;\n"
    "      text-decoration: underline;\n"
    "      padding: 24px 32px;\n"
    "      background: #fff8e1;\n"
    "      border: 3px solid #c62828;\n"
    "    }\n"
    "  </style>\n"
    "</head>\n"
    "<body>\n"
    "  <div class=\"wrap\">\n"
    "    <a class=\"probe\" href=\"https://browser.example/test-link\">&#x427;&#x418;&#x422;&#x410;&#x422;&#x42C;</a>\n"
    "  </div>\n"
    "</body>\n"
    "</html>\n";

struct BaselineWindows {
    HWND items[256];
    int count;
};

struct FindWindowCtx {
    const BaselineWindows* baseline;
    const wchar_t* title_substr;
    HWND found;
};

template <typename T>
void SafeRelease(T** value) {
    if (*value) {
        (*value)->Release();
        *value = nullptr;
    }
}

bool WideContains(const wchar_t* haystack, const wchar_t* needle) {
    return haystack != nullptr && needle != nullptr && wcsstr(haystack, needle) != nullptr;
}

bool IsBaselineWindow(const BaselineWindows* baseline, HWND hwnd) {
    if (!baseline) {
        return false;
    }
    for (int i = 0; i < baseline->count; ++i) {
        if (baseline->items[i] == hwnd) {
            return true;
        }
    }
    return false;
}

void PrintUtf8Line(const wchar_t* key, const wchar_t* value) {
    char utf8[4096];
    int written = WideCharToMultiByte(CP_UTF8, 0, value ? value : L"", -1, utf8, sizeof(utf8), nullptr, nullptr);
    if (written <= 0) {
        printf("%ls=\n", key);
        return;
    }
    printf("%ls=%s\n", key, utf8);
}

void PrintRectLine(const wchar_t* key, const RECT& rect) {
    printf("%ls=%ld,%ld,%ld,%ld\n", key, rect.left, rect.top, rect.right, rect.bottom);
}

bool IsProbeLinkName(const wchar_t* value) {
    static const wchar_t kProbeLinkName[] = {0x0427, 0x0418, 0x0422, 0x0410, 0x0422, 0x042C, 0};
    return value != nullptr && wcscmp(value, kProbeLinkName) == 0;
}

BOOL CALLBACK CollectBaselineProc(HWND hwnd, LPARAM lparam) {
    BaselineWindows* baseline = reinterpret_cast<BaselineWindows*>(lparam);
    if (!IsWindowVisible(hwnd)) {
        return TRUE;
    }
    wchar_t cls[256] = {};
    GetClassNameW(hwnd, cls, 255);
    if (wcscmp(cls, L"Chrome_WidgetWin_1") != 0) {
        return TRUE;
    }
    if (baseline->count < static_cast<int>(sizeof(baseline->items) / sizeof(baseline->items[0]))) {
        baseline->items[baseline->count++] = hwnd;
    }
    return TRUE;
}

BOOL CALLBACK FindProbeWindowProc(HWND hwnd, LPARAM lparam) {
    FindWindowCtx* ctx = reinterpret_cast<FindWindowCtx*>(lparam);
    if (!IsWindowVisible(hwnd)) {
        return TRUE;
    }
    wchar_t cls[256] = {};
    GetClassNameW(hwnd, cls, 255);
    if (wcscmp(cls, L"Chrome_WidgetWin_1") != 0) {
        return TRUE;
    }
    if (IsBaselineWindow(ctx->baseline, hwnd)) {
        return TRUE;
    }
    wchar_t title[512] = {};
    GetWindowTextW(hwnd, title, 511);
    if (!WideContains(title, ctx->title_substr)) {
        return TRUE;
    }
    ctx->found = hwnd;
    return FALSE;
}

BOOL CALLBACK FindRenderWindowProc(HWND hwnd, LPARAM lparam) {
    HWND* result = reinterpret_cast<HWND*>(lparam);
    wchar_t cls[256] = {};
    GetClassNameW(hwnd, cls, 255);
    if (wcscmp(cls, L"Chrome_RenderWidgetHostHWND") == 0) {
        *result = hwnd;
        return FALSE;
    }
    return TRUE;
}

HWND WaitForRenderWindow(HWND parent, DWORD timeout_ms) {
    const DWORD start = GetTickCount();
    while (GetTickCount() - start < timeout_ms) {
        HWND render = nullptr;
        EnumChildWindows(parent, FindRenderWindowProc, reinterpret_cast<LPARAM>(&render));
        if (render != nullptr) {
            return render;
        }
        Sleep(200);
    }
    return nullptr;
}

bool WriteProbeHtml(const wchar_t* html_path) {
    HANDLE file = CreateFileW(
        html_path,
        GENERIC_WRITE,
        0,
        nullptr,
        CREATE_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        nullptr
    );
    if (file == INVALID_HANDLE_VALUE) {
        return false;
    }
    DWORD written = 0;
    const DWORD size = static_cast<DWORD>(strlen(kHtmlTemplate));
    BOOL ok = WriteFile(file, kHtmlTemplate, size, &written, nullptr);
    CloseHandle(file);
    return ok && written == size;
}

bool BuildProbePaths(wchar_t* cwd, size_t cwd_len, wchar_t* html_path, size_t html_len, wchar_t* url, size_t url_len) {
    DWORD got = GetCurrentDirectoryW(static_cast<DWORD>(cwd_len), cwd);
    if (got == 0 || got >= cwd_len) {
        return false;
    }
    if (_snwprintf(html_path, html_len, L"%ls\\tmp_patch\\browser_uia_native_probe.html", cwd) < 0) {
        return false;
    }
    if (!CreateDirectoryW(L"tmp_patch", nullptr)) {
        DWORD err = GetLastError();
        if (err != ERROR_ALREADY_EXISTS) {
            return false;
        }
    }
    if (_snwprintf(url, url_len, L"file:///%ls/tmp_patch/browser_uia_native_probe.html", cwd) < 0) {
        return false;
    }
    for (wchar_t* p = url; *p; ++p) {
        if (*p == L'\\') {
            *p = L'/';
        }
    }
    return true;
}

bool LaunchEdge(const wchar_t* url, PROCESS_INFORMATION* pi) {
    wchar_t command[4096] = {};
    if (_snwprintf(
            command,
            sizeof(command) / sizeof(command[0]),
            L"\"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe\" --new-window \"%ls\" --window-position=120,80 --window-size=1200,900",
            url) < 0) {
        return false;
    }
    STARTUPINFOW si = {};
    si.cb = sizeof(si);
    ZeroMemory(pi, sizeof(*pi));
    return CreateProcessW(nullptr, command, nullptr, nullptr, FALSE, 0, nullptr, nullptr, &si, pi) == TRUE;
}

HWND WaitForProbeWindow(const BaselineWindows* baseline, DWORD timeout_ms) {
    const DWORD start = GetTickCount();
    while (GetTickCount() - start < timeout_ms) {
        FindWindowCtx ctx = {};
        ctx.baseline = baseline;
        ctx.title_substr = kProbeTitle;
        EnumWindows(FindProbeWindowProc, reinterpret_cast<LPARAM>(&ctx));
        if (ctx.found != nullptr) {
            return ctx.found;
        }
        Sleep(200);
    }
    return nullptr;
}

void CloseWindowIfAny(HWND hwnd) {
    if (hwnd) {
        PostMessageW(hwnd, WM_CLOSE, 0, 0);
    }
}

void CleanupProcess(PROCESS_INFORMATION* pi) {
    if (pi->hThread) {
        CloseHandle(pi->hThread);
        pi->hThread = nullptr;
    }
    if (pi->hProcess) {
        WaitForSingleObject(pi->hProcess, 5000);
        CloseHandle(pi->hProcess);
        pi->hProcess = nullptr;
    }
}

void DetachProcess(PROCESS_INFORMATION* pi) {
    if (pi->hThread) {
        CloseHandle(pi->hThread);
        pi->hThread = nullptr;
    }
    if (pi->hProcess) {
        CloseHandle(pi->hProcess);
        pi->hProcess = nullptr;
    }
}

HRESULT GetCurrentName(IUIAutomationElement* element, BSTR* out) {
    *out = nullptr;
    return element->get_CurrentName(out);
}

HRESULT GetCurrentValue(IUIAutomationElement* element, BSTR* out) {
    *out = nullptr;
    IUIAutomationValuePattern* pattern = nullptr;
    HRESULT hr = element->GetCurrentPatternAs(UIA_ValuePatternId, IID_PPV_ARGS(&pattern));
    if (FAILED(hr) || !pattern) {
        return hr;
    }
    hr = pattern->get_CurrentValue(out);
    pattern->Release();
    return hr;
}

int CountDescendants(IUIAutomationElement* root, IUIAutomation* automation) {
    IUIAutomationCondition* condition = nullptr;
    IUIAutomationElementArray* elements = nullptr;
    int count = -1;
    if (SUCCEEDED(automation->CreateTrueCondition(&condition)) &&
        SUCCEEDED(root->FindAll(TreeScope_Descendants, condition, &elements)) &&
        elements) {
        elements->get_Length(&count);
    }
    SafeRelease(&elements);
    SafeRelease(&condition);
    return count;
}

HRESULT FindHyperlink(IUIAutomation* automation, IUIAutomationElement* root, IUIAutomationElement** found, int* descendant_count) {
    *found = nullptr;
    *descendant_count = -1;
    IUIAutomationCondition* condition = nullptr;
    IUIAutomationElementArray* elements = nullptr;
    HRESULT hr = automation->CreateTrueCondition(&condition);
    if (FAILED(hr)) {
        return hr;
    }
    hr = root->FindAll(TreeScope_Descendants, condition, &elements);
    if (FAILED(hr) || !elements) {
        SafeRelease(&condition);
        return hr;
    }
    elements->get_Length(descendant_count);

    const int count = *descendant_count;
    for (int i = 0; i < count; ++i) {
        IUIAutomationElement* element = nullptr;
        if (FAILED(elements->GetElement(i, &element)) || !element) {
            continue;
        }
        CONTROLTYPEID type_id = 0;
        BSTR name = nullptr;
        if (SUCCEEDED(element->get_CurrentControlType(&type_id)) &&
            type_id == UIA_HyperlinkControlTypeId &&
            SUCCEEDED(GetCurrentName(element, &name)) &&
            name != nullptr &&
            IsProbeLinkName(name)) {
            *found = element;
            SysFreeString(name);
            SafeRelease(&elements);
            SafeRelease(&condition);
            return S_OK;
        }
        if (name) {
            SysFreeString(name);
        }
        element->Release();
    }

    SafeRelease(&elements);
    SafeRelease(&condition);
    return HRESULT_FROM_WIN32(ERROR_NOT_FOUND);
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
    bool leave_open = false;
    for (int i = 1; i < argc; ++i) {
        if (wcscmp(argv[i], L"--leave-open") == 0) {
            leave_open = true;
        }
    }

    wchar_t cwd[MAX_PATH] = {};
    wchar_t html_path[MAX_PATH] = {};
    wchar_t url[2048] = {};
    if (!BuildProbePaths(cwd, MAX_PATH, html_path, MAX_PATH, url, 2048)) {
        fprintf(stderr, "failed=build_paths\n");
        return 1;
    }
    if (!WriteProbeHtml(html_path)) {
        fprintf(stderr, "failed=write_probe_html\n");
        return 1;
    }

    BaselineWindows baseline = {};
    EnumWindows(CollectBaselineProc, reinterpret_cast<LPARAM>(&baseline));

    PROCESS_INFORMATION pi = {};
    if (!LaunchEdge(url, &pi)) {
        fprintf(stderr, "failed=launch_edge\n");
        return 1;
    }

    HWND probe_window = WaitForProbeWindow(&baseline, 15000);
    if (!probe_window) {
        TerminateProcess(pi.hProcess, 1);
        CleanupProcess(&pi);
        fprintf(stderr, "failed=probe_window_not_found\n");
        return 1;
    }

    Sleep(5000);

    HRESULT coinit_hr = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    HRESULT hr = coinit_hr;
    const bool coinit_ok = SUCCEEDED(coinit_hr) || coinit_hr == RPC_E_CHANGED_MODE;
    if (!coinit_ok) {
        CloseWindowIfAny(probe_window);
        CleanupProcess(&pi);
        fprintf(stderr, "failed=coinitialize\n");
        return 1;
    }

    IUIAutomation* automation = nullptr;
    IUIAutomationElement* top_element = nullptr;
    IUIAutomationElement* render_element = nullptr;
    IUIAutomationElement* hyperlink = nullptr;
    IUIAutomationElement* point_element = nullptr;
    HWND render_window = nullptr;
    BSTR top_name = nullptr;
    BSTR link_name = nullptr;
    BSTR link_value = nullptr;
    BSTR point_name = nullptr;
    BSTR point_value = nullptr;
    RECT link_rect = {};
    int top_descendants = -1;
    int render_descendants = -1;
    POINT center = {};
    int exit_code = 0;

    hr = CoCreateInstance(CLSID_CUIAutomation, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&automation));
    if (FAILED(hr) || !automation) {
        fprintf(stderr, "failed=cocreateinstance hr=0x%08lx\n", static_cast<unsigned long>(hr));
        exit_code = 1;
        goto cleanup;
    }

    hr = automation->ElementFromHandle(probe_window, &top_element);
    if (FAILED(hr) || !top_element) {
        fprintf(stderr, "failed=top_element hr=0x%08lx\n", static_cast<unsigned long>(hr));
        exit_code = 1;
        goto cleanup;
    }
    top_descendants = CountDescendants(top_element, automation);
    GetCurrentName(top_element, &top_name);

    hr = FindHyperlink(automation, top_element, &hyperlink, &render_descendants);
    if (FAILED(hr) || !hyperlink) {
        if (!render_window) {
            render_window = WaitForRenderWindow(probe_window, 15000);
        }
        if (!render_window) {
            fprintf(stderr, "failed=render_window_not_found\n");
            exit_code = 1;
            goto cleanup;
        }
        hr = automation->ElementFromHandle(render_window, &render_element);
        if (FAILED(hr) || !render_element) {
            fprintf(stderr, "failed=render_element hr=0x%08lx\n", static_cast<unsigned long>(hr));
            exit_code = 1;
            goto cleanup;
        }
        hr = FindHyperlink(automation, render_element, &hyperlink, &render_descendants);
    }
    if (FAILED(hr) || !hyperlink) {
        fprintf(stderr, "failed=hyperlink_not_found hr=0x%08lx\n", static_cast<unsigned long>(hr));
        exit_code = 1;
        goto cleanup;
    }

    GetCurrentName(hyperlink, &link_name);
    GetCurrentValue(hyperlink, &link_value);

    if (FAILED(hyperlink->get_CurrentBoundingRectangle(&link_rect))) {
        fprintf(stderr, "failed=bounding_rect\n");
        exit_code = 1;
        goto cleanup;
    }

    center.x = (link_rect.left + link_rect.right) / 2;
    center.y = (link_rect.top + link_rect.bottom) / 2;
    hr = automation->ElementFromPoint(center, &point_element);
    if (FAILED(hr) || !point_element) {
        fprintf(stderr, "failed=element_from_point hr=0x%08lx\n", static_cast<unsigned long>(hr));
        exit_code = 1;
        goto cleanup;
    }

    GetCurrentName(point_element, &point_name);
    GetCurrentValue(point_element, &point_value);

    printf("coinit_hr=0x%08lx\n", static_cast<unsigned long>(coinit_hr));
    printf("edge_pid=%lu\n", static_cast<unsigned long>(pi.dwProcessId));
    printf("top_window=0x%p\n", probe_window);
    printf("render_window=0x%p\n", render_window);
    printf("top_descendants=%d\n", top_descendants);
    printf("render_descendants=%d\n", render_descendants);
    PrintUtf8Line(L"top_name", top_name ? top_name : L"");
    PrintUtf8Line(L"link_name", link_name ? link_name : L"");
    PrintUtf8Line(L"link_value", link_value ? link_value : L"");
    PrintRectLine(L"link_rect", link_rect);
    printf("point_center=%ld,%ld\n", center.x, center.y);
    PrintUtf8Line(L"point_name", point_name ? point_name : L"");
    PrintUtf8Line(L"point_value", point_value ? point_value : L"");

cleanup:
    if (top_name) {
        SysFreeString(top_name);
    }
    if (link_name) {
        SysFreeString(link_name);
    }
    if (link_value) {
        SysFreeString(link_value);
    }
    if (point_name) {
        SysFreeString(point_name);
    }
    if (point_value) {
        SysFreeString(point_value);
    }
    SafeRelease(&point_element);
    SafeRelease(&hyperlink);
    SafeRelease(&render_element);
    SafeRelease(&top_element);
    SafeRelease(&automation);
    if (coinit_ok && coinit_hr != RPC_E_CHANGED_MODE) {
        CoUninitialize();
    }
    if (leave_open) {
        DetachProcess(&pi);
    } else {
        CloseWindowIfAny(probe_window);
        CleanupProcess(&pi);
    }
    return exit_code;
}
