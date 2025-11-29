import { 
  Code2, 
  HeartPulse, 
  Scale, 
  TrendingUp, 
  GraduationCap,
  Sparkles 
} from 'lucide-react';

export interface DomainConfig {
  id: string;
  name: string;
  shortName: string;
  description: string;
  icon: any;
  color: string;
  lightColor: string;
  darkColor: string;
  examplePrompts: string[];
  welcomeMessage: string;
}

export const domains: Record<string, DomainConfig> = {
  tech: {
    id: 'tech',
    name: 'SyroTech',
    shortName: 'Tech',
    description: 'Assistant expert en Data Engineering et technologies',
    icon: Code2,
    color: 'domain-tech',
    lightColor: 'domain-tech-light',
    darkColor: 'domain-tech-dark',
    examplePrompts: [
      'Comment optimiser une requête SQL sur Snowflake ?',
      'Explique-moi la différence entre pandas et PySpark',
      'Comment configurer un pipeline Airflow pour un ETL ?'
    ],
    welcomeMessage: 'Assistant spécialisé en Data Engineering, Python, SQL, Cloud et Architecture Data'
  },
  medical: {
    id: 'medical',
    name: 'SyroMed',
    shortName: 'Médical',
    description: 'Assistant expert en médecine et santé',
    icon: HeartPulse,
    color: 'domain-medical',
    lightColor: 'domain-medical-light',
    darkColor: 'domain-medical-dark',
    examplePrompts: [
      'Quels sont les symptômes de la grippe ?',
      'Explique-moi le mécanisme d\'action de l\'aspirine',
      'Quelle est la différence entre un virus et une bactérie ?'
    ],
    welcomeMessage: 'Assistant spécialisé en médecine, pathologies, diagnostics et traitements'
  },
  legal: {
    id: 'legal',
    name: 'SyroLegal',
    shortName: 'Juridique',
    description: 'Assistant expert en droit et jurisprudence',
    icon: Scale,
    color: 'domain-legal',
    lightColor: 'domain-legal-light',
    darkColor: 'domain-legal-dark',
    examplePrompts: [
      'Quels sont les droits du salarié en cas de licenciement ?',
      'Explique-moi la différence entre un contrat CDI et CDD',
      'Qu\'est-ce que le droit de rétractation ?'
    ],
    welcomeMessage: 'Assistant spécialisé en droit civil, commercial, pénal et réglementation'
  },
  finance: {
    id: 'finance',
    name: 'SyroFinance',
    shortName: 'Finance',
    description: 'Assistant expert en finance et économie',
    icon: TrendingUp,
    color: 'domain-finance',
    lightColor: 'domain-finance-light',
    darkColor: 'domain-finance-dark',
    examplePrompts: [
      'Comment calculer la valeur actuelle nette (VAN) ?',
      'Explique-moi la différence entre actions et obligations',
      'Qu\'est-ce que le ratio de liquidité ?'
    ],
    welcomeMessage: 'Assistant spécialisé en finance, comptabilité, investissements et analyse financière'
  },
  education: {
    id: 'education',
    name: 'SyroEdu',
    shortName: 'Éducation',
    description: 'Assistant expert en éducation et pédagogie',
    icon: GraduationCap,
    color: 'domain-education',
    lightColor: 'domain-education-light',
    darkColor: 'domain-education-dark',
    examplePrompts: [
      'Comment créer un plan de cours efficace ?',
      'Explique-moi les différentes méthodes pédagogiques',
      'Quels sont les principes de l\'apprentissage actif ?'
    ],
    welcomeMessage: 'Assistant spécialisé en pédagogie, méthodes d\'enseignement et ressources éducatives'
  },
  general: {
    id: 'general',
    name: 'Syro',
    shortName: 'Général',
    description: 'Assistant polyvalent',
    icon: Sparkles,
    color: 'primary',
    lightColor: 'primary-100',
    darkColor: 'primary-700',
    examplePrompts: [
      'Comment puis-je t\'aider aujourd\'hui ?',
      'Quels sont tes domaines d\'expertise ?',
      'Explique-moi comment tu fonctionnes'
    ],
    welcomeMessage: 'Assistant intelligent et polyvalent'
  }
};

export const getDomainConfig = (domainId: string): DomainConfig => {
  return domains[domainId] || domains.general;
};

