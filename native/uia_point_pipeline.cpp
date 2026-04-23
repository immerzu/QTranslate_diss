#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <ole2.h>
#include <UIAutomation.h>

extern "C" HRESULT __stdcall qtranslate_uia_point_resolve(
    IUIAutomation* automation,
    LONG x,
    LONG y,
    BSTR* out_name,
    BSTR* out_value,
    CONTROLTYPEID* out_type) {
    if (!automation || !out_name || !out_value || !out_type) {
        return E_INVALIDARG;
    }

    *out_name = nullptr;
    *out_value = nullptr;
    *out_type = 0;

    POINT point = {};
    point.x = x;
    point.y = y;

    IUIAutomationElement* element = nullptr;
    HRESULT hr = automation->ElementFromPoint(point, &element);
    if (FAILED(hr) || !element) {
        return FAILED(hr) ? hr : E_FAIL;
    }

    hr = element->get_CurrentControlType(out_type);
    if (FAILED(hr)) {
        element->Release();
        return hr;
    }

    hr = element->get_CurrentName(out_name);
    if (FAILED(hr)) {
        element->Release();
        return hr;
    }

    IUIAutomationValuePattern* value_pattern = nullptr;
    hr = element->GetCurrentPatternAs(UIA_ValuePatternId, IID_PPV_ARGS(&value_pattern));
    if (FAILED(hr) || !value_pattern) {
        element->Release();
        return FAILED(hr) ? hr : E_NOINTERFACE;
    }

    hr = value_pattern->get_CurrentValue(out_value);
    value_pattern->Release();
    element->Release();
    return hr;
}
