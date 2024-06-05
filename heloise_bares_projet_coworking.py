# Importation des bibliotheques necessaires
import requests  # Pour envoyer des requetes HTTP
from bs4 import BeautifulSoup  # pour analyser le HTML
import pandas as pd  # pour manipuler les donnees sous forme de tableaux
import re  # pour le nettoyage des donnees avec des expressions regulieres
import numpy as np  # pour les operations mathematiques et le traitement des donnees manquantes
from geopy.geocoders import Nominatim  # pour la geolocalisation
from geopy.extra.rate_limiter import RateLimiter  # pour limiter le taux des requetes de geolocalisation
from geopy.exc import GeocoderTimedOut, GeocoderServiceError  # pour gerer les erreurs de geolocalisation
import folium  # pour creer des cartes interactives
import streamlit as st  # pour creer des applications web interactives
from streamlit_folium import folium_static  # pour afficher des cartes Folium dans Streamlit
import time  # pour gerer les delais et les temps d'attente
import matplotlib.pyplot as plt  # pour creer des graphiques



# Fonction pour nettoyer les numeros de téléphone
def nettoyer_tel(tel):
    if tel:  # Vérifier si le numéro de téléphone n'est pas vide
        tel = tel.strip()  # Supprimer les espaces en début et fin de numéro
        tel = re.sub(r'[:\s]', '', tel)  # Supprimer les deux-points et les espaces
        return tel  # Retourner le numéro de téléphone nettoyé
    return np.nan  # Retourner NaN si le numéro est vide

# Fonction pour nettoyer les adresses
def nettoyer_adresse(adresse):
    if adresse:  # Vérifier si l'adresse n'est pas vide
        adresse = re.sub(r'^\s*-?', '', adresse)  # Supprimer les tirets et espaces en début d'adresse
        adresse = re.sub(r'^:\s*', '', adresse)  # Supprimer les deux-points en début d'adresse
        return adresse # Retourner l'adresse nettoyée
    return np.nan  # Retourner NaN si l'adresse est vide

# Fonction pour nettoyer les noms
def nettoyer_nom(nom):
    if nom:  # Vérifier si le nom n'est pas vide
        nom = nom.split(':')[0].strip()  # Prendre la partie avant les deux-points et supprimer les espaces
        return nom  # Retourner le nom nettoyé
    return np.nan  # Retourner NaN si le nom est vide


# Fonction pour extraire les informations d'une page HTML
def extract_info(label, soup):
    strong_tag = soup.find('strong', string=lambda text: text and label in text)  # Trouver un élément 'strong' contenant le label
    if strong_tag and strong_tag.next_sibling:  # Si l'élément est trouvé et a un frère
        return strong_tag.next_sibling.strip()  # Retourner le texte du frère nettoyé
    li_tag = soup.find('li', string=lambda text: text and label in text)  # Trouver un élément 'li' contenant le label
    if li_tag:  # Si l'élément est trouvé
        return li_tag.text.split(': ', 1)[-1].strip()  # Retourner le texte après les deux-points nettoyé
    return 'Non Disponible'  # Retourner 'Non Disponible' si aucune information n'est trouvée



# URL de base pour les requetes
base_url = 'https://www.leportagesalarial.com/coworking/'

# Récupération de la page principale
response = requests.get(base_url)  # Envoyer une requete HTTP GET
soup = BeautifulSoup(response.text, 'html.parser')  # Analyser le contenu HTML de la réponse

# Recherche des liens qui contiennent 'Paris' 
liens = soup.find_all('a', string=lambda text: 'Paris' in text if text else False)  # Trouver tous les liens contenant 'Paris'

# Ensemble pour stocker les URL déjà traitées
url_traitees = set()  # Initialiser un ensemble vide

# Liste pour stocker les données
donnees = []  # Initialiser une liste vide




# Pour chaque lien trouvé, accéder à la page et extraire les informations
for lien in liens:
    url = lien.get('href')  # Récupérer l'URL du lien
    if url not in url_traitees:  # Vérifier si l'URL n'a pas été déjà traitée
        url_traitees.add(url)  # Ajouter l'URL à l'ensemble des URL traitées
        response = requests.get(url)  # Envoyer une requete HTTP GET
        page_soup = BeautifulSoup(response.text, 'html.parser')  # Analyser le contenu HTML de la réponse

        # Extraire les informations de chaque page de coworking
        titre = page_soup.find('h1').text.strip() if page_soup.find('h1') else 'Non Disponible'  # Extraire le titre
        adresse = extract_info('Adresse', page_soup)  # Extraire l'adresse
        tel = extract_info('Téléphone', page_soup)  # Extraire le téléphone

        # Nettoyer les données
        title = nettoyer_nom(titre)  # Nettoyer le nom
        adresse = nettoyer_adresse(adresse)  # Nettoyer l'adresse
        tel = nettoyer_tel(tel)  # Nettoyer le téléphone

        # Ajouter les informations au dataset
        donnees.append({
            'Nom': titre,  # Nom du coworking
            'URL': url,  # URL de la page
            'Adresse': adresse,  # Adresse du coworking
            'Téléphone': tel,  # Numéro de téléphone du coworking
        })

# Convertir en DataFrame
df = pd.DataFrame(donnees)  # Convertir la liste de données en DataFrame




# Utiliser l'API Nominatim pour obtenir les coordonnées géographiques
geolocator = Nominatim(user_agent="coworking_locator")  # Initialiser le géolocalisateur
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)  # Limiter le taux de requetes

# Fonction pour géolocaliser en toute sécurité
def safe_geocode(address):
    for attempt in range(3):  # Essayer 3 fois
        try:
            return geocode(address)  # Tenter de géolocaliser
        except (GeocoderTimedOut, GeocoderServiceError):  # En cas d'erreur
            time.sleep(2)  # Attendre 2 secondes avant de réessayer
    return None  # Retourner None après 3 échecs

# Ajouter une colonne 'Adresse complète' au DataFrame
df['Adresse complète'] = df['Adresse'] + ', Paris, France'  # Combiner l'adresse avec 'Paris, France'
df['Localisation'] = df['Adresse complète'].apply(safe_geocode)  # Appliquer la géolocalisation
df['Latitude'] = df['Localisation'].apply(lambda loc: loc.latitude if loc else None)  # Extraire la latitude
df['Longitude'] = df['Localisation'].apply(lambda loc: loc.longitude if loc else None)  # Extraire la longitude

# Supprimer les colonnes intermédiaires
df.drop(columns=['Adresse complète', 'Localisation'], inplace=True)  # Supprimer les colonnes inutiles

# Enregistrer les résultats dans un fichier Excel
df.to_excel("coworking_paris.xlsx", index=False)  # Enregistrer le DataFrame dans un fichier Excel


print(df)  # Afficher le DataFrame sur le terminal 









# Charger les données
df2 = pd.read_excel("coworking_paris.xlsx")  # Charger le fichier Excel

# Vérifiez que le DataFrame n'est pas vide
if not df2.empty:
    # Créer une carte Folium centrée sur Paris
    m = folium.Map(location=[48.8566, 2.3522], zoom_start=12)  # Initialiser la carte

    # Ajouter les marqueurs pour chaque espace de coworking
    for _, row in df2.iterrows():  # Parcourir chaque ligne du DataFrame
        if not pd.isna(row['Latitude']) and not pd.isna(row['Longitude']):  # Vérifier que les coordonnées sont disponibles
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],  # Position du marqueur
                popup=f"{row['Nom']}<br>{row['Adresse']}<br>{row['Téléphone']}",  # Contenu du popup
                icon=folium.Icon(color='blue')  # Icone du marqueur
            ).add_to(m)  # Ajouter le marqueur à la carte

    # Afficher la carte dans Streamlit
    st.title("Espaces de Coworking à Paris")  # Titre de l'application
    folium_static(m)  # Afficher la carte




    

    # Ajout de visualisations des données
    st.subheader("Données des Espaces de Coworking")  # Sous-titre des visualisations

    # Extraction du code postal et de l'arrondissement
    df2['Code Postal'] = df2['Adresse'].str.extract(r'(\d{5})')[0]  # Extraire le code postal
    df2['Arrondissement'] = df2['Code Postal'].str[3:5]  # Extraire les deux derniers chiffres du code postal

    # Nombre d'espaces de coworking par arrondissement
    arr_count = df2['Arrondissement'].value_counts()  # Compter le nombre d'espaces par arrondissement

    fig, ax = plt.subplots()  # Créer une figure
    arr_count.plot(kind='bar', ax=ax)  # Créer un graphique à barres
    ax.set_title('Nombre d\'Espaces de Coworking par Arrondissement')  # Titre du graphique
    ax.set_xlabel('Arrondissement')  # Label de l'axe X
    ax.set_ylabel('Nombre d\'Espaces')  # Label de l'axe Y

    st.pyplot(fig)  # Afficher le graphique

    # Tableau des espaces de coworking
    st.subheader("Tableau des Espaces de Coworking")  # Sous-titre du tableau
    st.dataframe(df2)  # Afficher le DataFrame

else:
    st.write("Aucun espace de coworking trouvé.")  # Message si aucun espace n'est trouvé
