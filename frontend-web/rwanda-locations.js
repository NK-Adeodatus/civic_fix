// Rwanda Administrative Divisions Data
const rwandaLocations = {
    "Kigali": {
        "Gasabo": [
            "Bumbogo", "Gatsata", "Jali", "Gikomero", "Gisozi", "Jabana", 
            "Kinyinya", "Ndera", "Nduba", "Rusororo", "Rutunga"
        ],
        "Kicukiro": [
            "Gahanga", "Gatenga", "Gikondo", "Kagarama", "Kanombe", "Kicukiro", 
            "Kigarama", "Masaka", "Niboye", "Nyarugunga"
        ],
        "Nyarugenge": [
            "Gitega", "Kanyinya", "Kigali", "Kimisagara", "Mageragere", "Muhima", 
            "Nyakabanda", "Nyamirambo", "Rwezamenyo", "Nyarugenge"
        ]
    },
    "Eastern": {
        "Bugesera": [
            "Gashora", "Juru", "Kamabuye", "Ntarama", "Mareba", "Mayange", 
            "Musenyi", "Mwogo", "Ngeruka", "Nyamata", "Nyarugenge", "Rilima", 
            "Ruhuha", "Rweru", "Shyara"
        ],
        "Gatsibo": [
            "Gasange", "Gatsibo", "Gitoki", "Kabarore", "Kageyo", "Kiramuruzi", 
            "Kiziguro", "Muhura", "Murambi", "Nyagihanga", "Remera", "Rugarama", "Rwimbogo"
        ],
        "Kayonza": [
            "Gahini", "Kabare", "Kabarondo", "Mukarange", "Murama", "Murundi", 
            "Mwiri", "Ndego", "Nyamirama", "Rukara", "Ruramira", "Rwinkwavu"
        ],
        "Kirehe": [
            "Gahara", "Gatore", "Kigarama", "Kigina", "Kirehe", "Mahama", 
            "Mpanga", "Musaza", "Mushikiri", "Nasho", "Nyamugari", "Nyarubuye"
        ],
        "Ngoma": [
            "Gashanda", "Jarama", "Karembo", "Kazo", "Kibungo", "Mugesera", 
            "Murama", "Mutenderi", "Remera", "Rukira", "Rukumberi", "Rurenge", "Sake", "Zaza"
        ],
        "Nyagatare": [
            "Rwimiyaga", "Karangazi", "Nyagatare", "Katabagemu", "Rukomo", "Tabagwe", 
            "Musheli", "Gatunda", "Mimuli", "Karama", "Matimba", "Mukama", "Rwempasha", "Kiyombe"
        ],
        "Rwamagana": [
            "Fumbwe", "Gahengeri", "Gishari", "Karenge", "Kigabiro", "Muhazi", 
            "Munyaga", "Munyiginya", "Musha", "Muyumbu", "Mwulire", "Nyakariro", "Nzige", "Rubona"
        ]
    },
    "Northern": {
        "Burera": [
            "Bungwe", "Butaro", "Cyanika", "Cyeru", "Gahunga", "Gatebe", "Gitovu", 
            "Kagogo", "Kinoni", "Kinyababa", "Kivuye", "Nemba", "Rugarama", 
            "Rugendabari", "Ruhunde", "Rusarabuge", "Rwerere"
        ],
        "Gakenke": [
            "Busengo", "Coko", "Cyabingo", "Gakenke", "Gashenyi", "Mugunga", "Janja", 
            "Kamubuga", "Karambo", "Kivuruga", "Mataba", "Minazi", "Muhondo", 
            "Muyongwe", "Muzo", "Nemba", "Ruli", "Rusasa", "Rushashi"
        ],
        "Gicumbi": [
            "Bukure", "Bwisige", "Byumba", "Cyumba", "Giti", "Kaniga", "Manyagiro", 
            "Miyove", "Kageyo", "Mukarange", "Muko", "Mutete", "Nyamiyaga", 
            "Nyankenke II", "Rubaya", "Rukomo", "Rushaki", "Rutare", "Ruvune", "Rwamiko", "Shangasha"
        ],
        "Musanze": [
            "Busogo", "Cyuve", "Gacaca", "Gashaki", "Gataraga", "Kimonyi", "Kinigi", 
            "Muhoza", "Muko", "Musanze", "Nkotsi", "Nyange", "Remera", "Rwaza", "Shingiro"
        ],
        "Rulindo": [
            "Base", "Burega", "Bushoki", "Buyoga", "Cyinzuzi", "Cyungo", "Kinihira", 
            "Kisaro", "Masoro", "Mbogo", "Murambi", "Ngoma", "Ntarabana", "Rukozo", "Rusiga", "Shyorongi", "Tumba"
        ]
    },
    "Southern": {
        "Gisagara": [
            "Gikonko", "Gishubi", "Kansi", "Kibilizi", "Kigembe", "Mamba", 
            "Muganza", "Mugombwa", "Mukindo", "Musha", "Ndora", "Nyanza", "Save"
        ],
        "Huye": [
            "Gishamvu", "Karama", "Kigoma", "Kinazi", "Maraba", "Mbazi", 
            "Mukura", "Ngoma", "Ruhashya", "Rusatira"
        ],
        "Kamonyi": [
            "Gacurabwenge", "Karama", "Kayenzi", "Kayumbu", "Mugina", "Musambira", 
            "Ngamba", "Nyamiyaga", "Nyarubaka", "Rugalika", "Rukoma", "Runda"
        ],
        "Muhanga": [
            "Cyeza", "Kabacuzi", "Kibangu", "Kiyumba", "Muhanga", "Mushishiro", 
            "Nyabinoni", "Nyamabuye", "Nyarusange", "Rongi"
        ],
        "Nyamagabe": [
            "Buruhukiro", "Cyanika", "Gatare", "Kaduha", "Kamegeli", "Kibirizi", 
            "Kibumbwe", "Kitabi", "Mbazi", "Mugano", "Musange", "Musebeya", 
            "Mushubi", "Nkomane", "Gasaka", "Tare", "Uwinkingi"
        ],
        "Nyanza": [
            "Busasamana", "Busoro", "Cyabakamyi", "Kibirizi", "Kigoma", "Mukingo", 
            "Ntyazo", "Nyagisozi", "Rwabicuma", "Muyira"
        ],
        "Nyaruguru": [
            "Cyahinda", "Busanze", "Kibeho", "Mata", "Munini", "Kivu", "Ngera", 
            "Ngoma", "Nyabimata", "Nyagisozi", "Muganza", "Ruheru", "Ruramba", "Rusenge"
        ],
        "Ruhango": [
            "Kinazi", "Byimana", "Bweramana", "Mbuye", "Ruhango", "Mwendo", "Kinihira"
        ]
    },
    "Western": {
        "Karongi": [
            "Bwishyura", "Gishari", "Gishyita", "Gisovu", "Gitesi", "Mubuga", 
            "Murambi", "Murundi", "Mutuntu", "Rubengera", "Rugabano", "Ruganda", "Rwankuba", "Twumba"
        ],
        "Ngororero": [
            "Bwira", "Gatumba", "Hindiro", "Kabaya", "Kageyo", "Kavumu", 
            "Matyazo", "Muhanda", "Muhororo", "Ndaro", "Ngororero", "Nyange", "Sovu"
        ],
        "Nyabihu": [
            "Bigogwe", "Jenda", "Jomba", "Kabatwa", "Karago", "Kintobo", 
            "Mukamira", "Muringa", "Rambura", "Rugera", "Rurembo", "Shyira"
        ],
        "Nyamasheke": [
            "Bushekeri", "Bushenge", "Cyato", "Gihombo", "Kagano", "Kanjongo", 
            "Karambi", "Karengera", "Kirimbi", "Macuba", "Nyabitekeri", "Mahembe", "Rangiro", "Shangi", "Ruharambuga"
        ],
        "Rubavu": [
            "Bugeshi", "Busasamana", "Cyanzarwe", "Gisenyi", "Kanama", "Kanzenze", 
            "Mudende", "Nyakiliba", "Nyamyumba", "Nyundo", "Rubavu", "Rugerero"
        ],
        "Rusizi": [
            "Bugarama", "Butare", "Bweyeye", "Gikundamvura", "Gashonga", "Giheke", 
            "Gihundwe", "Gitambi", "Kamembe", "Muganza", "Mururu", "Nkanka", 
            "Nkombo", "Nkungu", "Nyakabuye", "Nyakarenzo", "Nzahaha", "Rwimbogo"
        ],
        "Rutsiro": [
            "Boneza", "Gihango", "Kigeyo", "Kivumu", "Manihira", "Mukura", 
            "Murunda", "Musasa", "Mushonyi", "Mushubati", "Nyabirasi", "Ruhango", "Rusebeya"
        ]
    }
};

// Helper functions for location management
class LocationManager {
    static getProvinces() {
        return Object.keys(rwandaLocations);
    }

    static getDistricts(province) {
        return province ? Object.keys(rwandaLocations[province] || {}) : [];
    }

    static getSectors(province, district) {
        return (province && district) ? (rwandaLocations[province]?.[district] || []) : [];
    }

    static getAllDistricts() {
        const allDistricts = [];
        for (const province in rwandaLocations) {
            for (const district in rwandaLocations[province]) {
                allDistricts.push(district);
            }
        }
        return allDistricts.sort();
    }

    static getAllSectors() {
        const allSectors = [];
        for (const province in rwandaLocations) {
            for (const district in rwandaLocations[province]) {
                allSectors.push(...rwandaLocations[province][district]);
            }
        }
        return [...new Set(allSectors)].sort();
    }

    static findProvinceByDistrict(district) {
        for (const province in rwandaLocations) {
            if (rwandaLocations[province][district]) {
                return province;
            }
        }
        return null;
    }

    static findDistrictBySector(sector) {
        for (const province in rwandaLocations) {
            for (const district in rwandaLocations[province]) {
                if (rwandaLocations[province][district].includes(sector)) {
                    return { province, district };
                }
            }
        }
        return null;
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { rwandaLocations, LocationManager };
}
