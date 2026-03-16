const dictionaries = {
  en: () => import("../../dictionaries/en.json").then((m) => m.default),
  fil: () => import("../../dictionaries/fil.json").then((m) => m.default),
  "zh-hant": () =>
    import("../../dictionaries/zh-hant.json").then((m) => m.default),
};

export type Locale = keyof typeof dictionaries;
export const locales = Object.keys(dictionaries) as Locale[];

export const getDictionary = async (locale: Locale) => {
  if (!dictionaries[locale]) {
    return dictionaries.en();
  }
  return dictionaries[locale]();
};

export type Dictionary = Awaited<ReturnType<typeof getDictionary>>;
