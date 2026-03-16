"use client";

import { useEffect } from "react";

export default function RootPage() {
  useEffect(() => {
    const lang = navigator.language || "en";
    let locale = "en";
    if (/zh/i.test(lang)) locale = "zh-hant";
    else if (/fil|tl/i.test(lang)) locale = "fil";
    window.location.replace(`/${locale}/`);
  }, []);

  return null;
}
