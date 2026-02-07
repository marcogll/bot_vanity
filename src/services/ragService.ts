import * as fs from 'fs';
import * as path from 'path';
import { Service, Location, SearchContext } from '../types';

export class RAGService {
  private services: Service[] = [];
  private locations: Location[] = [];
  private readonly OLD_PROMO_KEYWORDS = [
    'Navidad',
    'Diciembre',
    'Octubre',
    '2023',
    '2024',
    '2025'
  ];
  private readonly FEBRUARY_CATEGORY = '💘 HELLO FEBRUARY 💘';

  constructor() {
    this.loadData();
  }

  private loadData(): void {
    try {
      const servicesPath = path.join(__dirname, '../../vanity_data/services.jsonl');
      const locationsPath = path.join(__dirname, '../../vanity_data/locations.jsonl');

      const servicesData = fs.readFileSync(servicesPath, 'utf-8').trim().split('\n');
      const locationsData = fs.readFileSync(locationsPath, 'utf-8').trim().split('\n');

      this.services = servicesData
        .map(line => JSON.parse(line))
        .filter((service: Service) => this.filterValidService(service));

      this.locations = locationsData.map(line => JSON.parse(line));

      console.log(`✅ Loaded ${this.services.length} services and ${this.locations.length} locations`);
    } catch (error) {
      console.error('❌ Error loading data:', error);
    }
  }

  private filterValidService(service: Service): boolean {
    const searchText = `${service.category} ${service.service}`.toLowerCase();
    
    const hasOldPromo = this.OLD_PROMO_KEYWORDS.some(keyword =>
      searchText.includes(keyword.toLowerCase())
    );

    return !hasOldPromo;
  }

  private calculateRelevanceScore(text: string, query: string): number {
    const queryLower = query.toLowerCase();
    const textLower = text.toLowerCase();
    
    const words = queryLower.split(/\s+/);
    let score = 0;
    
    words.forEach(word => {
      if (word.length < 2) return;
      
      if (textLower.includes(word)) {
        score += 1;
      }
      
      if (textLower.startsWith(word)) {
        score += 0.5;
      }
    });

    return score;
  }

  search(query: string): SearchContext {
    const queryLower = query.toLowerCase();
    
    let relevantServices = this.services.map(service => ({
      service,
      score: this.calculateRelevanceScore(
        `${service.category} ${service.service} ${service.description}`,
        query
      )
    }));

    let relevantLocations = this.locations.map(location => ({
      location,
      score: this.calculateRelevanceScore(
        `${location.name} ${location.zone} ${location.description} ${location.address || ''}`,
        query
      )
    }));

    const isQueryAboutPromos = queryLower.includes('promo') || 
                               queryLower.includes('oferta') ||
                               queryLower.includes('descuento') ||
                               queryLower.includes('paquete');

    if (isQueryAboutPromos) {
      relevantServices = relevantServices.map(item => ({
        ...item,
        score: item.service.category === this.FEBRUARY_CATEGORY ? item.score + 3 : item.score
      }));
    }

    const topServices = relevantServices
      .filter(item => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 5)
      .map(item => item.service);

    const topLocations = relevantLocations
      .filter(item => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 2)
      .map(item => item.location);

    return {
      services: topServices,
      locations: topLocations
    };
  }

  getAllFebruaryPromos(): Service[] {
    return this.services.filter(s => s.category === this.FEBRUARY_CATEGORY);
  }

  getLocationByName(name: string): Location | undefined {
    const nameLower = name.toLowerCase();
    return this.locations.find(loc => 
      loc.name.toLowerCase().includes(nameLower) ||
      loc.zone?.toLowerCase().includes(nameLower)
    );
  }
}

export const ragService = new RAGService();
