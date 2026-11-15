import { Building2, Scale, UtensilsCrossed, BedDouble, Store } from "lucide-react";

const IMG = "https://static.prod-images.emergentagent.com/jobs/ce98ddb4-55cd-4f9c-a6a9-cb2cc7509471/images";

export const HOME_HERO_IMG = `${IMG}/02331550e24d597916726cf079d3bda49d1b0262a92629f9b098e91507ac2415.jpeg`;
export const LEGAL_HERO_IMG = `${IMG}/d65472c77fb5f72d5d7c6e7146310eea4dc6be0a8812c5fec0695c4e8ca37a92.jpeg`;

export const SERVICES = [
  {
    key: "auditorias",
    icon: Building2,
    tag: "Inteligencia artificial",
    title: "Auditorías con IA para condominios",
    desc: "Sube facturas, estados de cuenta y recibos. La IA cruza cada documento, detecta irregularidades y entrega un informe profesional en PDF.",
    href: "/auditorias-condominios",
    cta: "Ver el servicio",
    image:
      "https://images.unsplash.com/photo-1479839672679-a46483c0e7c8?crop=entropy&cs=srgb&fm=jpg&q=70&w=1200",
  },
  {
    key: "legal",
    icon: Scale,
    tag: "Legal y contable",
    title: "Asesoría legal y contable especializada",
    desc: "Expediente digital con seguimiento de tu caso, generación y procesamiento de documentos: desalojos, denuncias, pensión de alimentos y más.",
    href: "/asesoria-legal",
    cta: "Ver el servicio",
    image: LEGAL_HERO_IMG,
  },
  {
    key: "restaurantes",
    icon: UtensilsCrossed,
    tag: "Gusto Peruano",
    title: "Menús digitales y páginas premium para restaurantes",
    desc: "Carta digital con QR, fotos de tus platos y una página propia que hace ver a tu restaurante como una marca grande.",
    href: "https://www.gustoperuano.com",
    external: true,
    cta: "Visitar gustoperuano.com",
    image: `${IMG}/becfdd70839574c45a0d203965b104db40b857fadaf64acdfab997477e71e3ba.jpeg`,
  },
  {
    key: "hoteles",
    icon: BedDouble,
    tag: "Hoteles QR",
    title: "Menús digitales y páginas premium para hoteles",
    desc: "Room service, servicios e información del hotel en un QR dentro de cada habitación, con página premium para tus huéspedes.",
    href: "https://www.hotelesqr.com",
    external: true,
    cta: "Visitar hotelesqr.com",
    image: `${IMG}/f763e1f2a8b2f44d44fa621d3c96d92c0b47ae83862dcce685bdfe405dcf4a23.jpeg`,
  },
  {
    key: "tiendas",
    icon: Store,
    tag: "Tienda Fácil QR",
    title: "Catálogos digitales QR para tiendas pequeñas",
    desc: "Tu catálogo de productos con precios en un QR: tus clientes lo escanean, eligen y te piden por WhatsApp.",
    href: "https://www.tiendafacilqr.com",
    external: true,
    cta: "Visitar tiendafacilqr.com",
    image: `${IMG}/c840076fef75c3c96e9af74f847000b44a2db22e9487ec97728c86d869bff568.jpeg`,
  },
];

export const serviceByKey = (key) => SERVICES.find((s) => s.key === key) || SERVICES[1];
