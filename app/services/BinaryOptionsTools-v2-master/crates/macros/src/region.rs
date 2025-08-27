use darling::{util::Override, FromDeriveInput};
use proc_macro2::{Span, TokenStream};
use quote::{quote, ToTokens};
use serde::Deserialize;
use std::collections::HashSet;
use std::fs::File;
use std::hash::Hash;
use std::io::Read;
use std::path::{Path, PathBuf};
use syn::Ident;
use url::Url;

#[derive(Debug, FromDeriveInput)]
#[darling(attributes(region))]
pub struct RegionImpl {
    ident: Ident,
    path: Override<PathBuf>,
}

#[derive(Debug, Deserialize)]
struct Regions(HashSet<Region>);

#[derive(Debug, Deserialize)]
struct Region {
    name: String,
    url: Url,
    latitude: f64,
    longitude: f64,
    demo: bool,
}

impl RegionImpl {
    fn regions(&self) -> anyhow::Result<Regions> {
        // Исходный путь из атрибута
        let raw_path = self
            .path
            .as_ref()
            .explicit()
            .ok_or(anyhow::anyhow!("Error"))?
            .clone();

        // Кандидаты разрешения пути
        let mut candidates: Vec<PathBuf> = Vec::new();

        // 1) Как есть (на случай абсолютного или уже корректного относительного)
        candidates.push(raw_path.clone());

        // 2) Относительно CARGO_MANIFEST_DIR текущего процесса (обычно макро-крейт)
        if raw_path.is_relative() {
            if let Ok(manifest_dir) = std::env::var("CARGO_MANIFEST_DIR") {
                candidates.push(PathBuf::from(manifest_dir).join(&raw_path));
            }
        }

        // 3) Относительно файла, где используется деривация (путь к regions.rs целевого крейта)
        if raw_path.is_relative() {
            let source_file_path = self.ident.span().unwrap().source_file().path();
            let base = source_file_path.parent().unwrap_or(Path::new("."));
            candidates.push(base.join(&raw_path));
        }

        // Открываем первый существующий
        let mut last_err: Option<anyhow::Error> = None;
        for p in candidates {
            match File::open(&p) {
                Ok(mut file) => {
                    let mut buff = String::new();
                    file.read_to_string(&mut buff)?;
                    return Ok(serde_json::from_str(&buff)?);
                }
                Err(e) => {
                    last_err = Some(anyhow::anyhow!("{}: {}", p.display(), e));
                }
            }
        }

        Err(last_err.unwrap_or_else(|| anyhow::anyhow!("regions.json not found")))
    }
}

impl ToTokens for RegionImpl {
    fn to_tokens(&self, tokens: &mut TokenStream) {
        let name = &self.ident;
        let implementation = &self.regions().unwrap();

        tokens.extend(quote! {
            impl #name {
                #implementation
            }
        });
    }
}

impl ToTokens for Regions {
    fn to_tokens(&self, tokens: &mut TokenStream) {
        let regions: &Vec<&Region> = &self.0.iter().collect();
        let demos: Vec<&Region> = regions.iter().filter_map(|r| r.get_demo()).collect();
        let demos_stream = demos.iter().map(|r| r.to_stream());
        let demos_url = demos.iter().map(|r| r.url());
        let reals: Vec<&Region> = regions.iter().filter_map(|r| r.get_real()).collect();
        let reals_stream = reals.iter().map(|r| r.to_stream());
        let reals_url = reals.iter().map(|r| r.url());

        tokens.extend(quote! {
            #(#regions)*

            pub fn demo_regions() -> Vec<(&'static str, f64, f64)> {
                vec![#(#demos_stream),*]
            }

            pub fn regions() -> Vec<(&'static str, f64, f64)> {
                vec![#(#reals_stream),*]
            }

            pub fn demo_regions_str() -> Vec<&'static str> {
                ::std::vec::Vec::from([#(#demos_url),*])
            }

            pub fn regions_str() -> Vec<&'static str> {
                ::std::vec::Vec::from([#(#reals_url),*])
            }
        });
    }
}

impl ToTokens for Region {
    fn to_tokens(&self, tokens: &mut TokenStream) {
        let name = self.name();
        let url = &self.url.to_string();
        let latitude = self.latitude;
        let longitude = self.longitude;
        tokens.extend(quote! {
            pub const #name: (&str, f64, f64) = (#url, #latitude, #longitude);
        });
    }
}

impl PartialEq for Region {
    fn eq(&self, other: &Self) -> bool {
        self.name == other.name
    }
}

impl Eq for Region {}

impl Hash for Region {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.name.hash(state);
    }
}

impl Region {
    fn name(&self) -> Ident {
        Ident::new(&self.name.to_uppercase(), Span::call_site())
    }

    fn url(&self) -> TokenStream {
        let name = self.name();
        quote! {
            Self::#name.0
        }
    }

    fn to_stream(&self) -> TokenStream {
        let name = self.name();
        quote! {
            Self::#name
        }
    }

    fn get_demo(&self) -> Option<&Self> {
        if self.demo {
            Some(self)
        } else {
            None
        }
    }

    fn get_real(&self) -> Option<&Self> {
        if !self.demo {
            Some(self)
        } else {
            None
        }
    }
}
