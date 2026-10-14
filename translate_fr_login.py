import json

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/fr/messages.json', 'r', encoding='utf-8') as f:
    fr = json.load(f)

translations = {
    'login.1': 'Planned Education',
    'login.2': 'Connectez-vous à votre compte',
    'login.3': 'Adresse e-mail',
    'login.4': 'Entrez votre e-mail',
    'login.5': 'Mot de passe',
    'login.6': 'Entrez votre mot de passe',
    'login.7': 'Se connecter',
    'login.8': 'ou',
    'login.9': 'Continuer avec Google',
    'login.10': 'Pas encore de compte ?',
    'login.11': "S'inscrire",
    'login.12': 'Mot de passe oublié ?',
    'login.13': 'Navigateur d\'examen sécurisé requis pour les examens',
    'login.14': 'La connexion Google n\'est pas configurée.',
    'login.15': 'S\'inscrire ici',
    'login.16': 'L\'e-mail ou le mot de passe est incorrect',
    'login.17': 'Compte non trouvé',
    'login.18': 'Trop de tentatives, veuillez réessayer plus tard',
    'register.1': 'Créer votre compte',
    'register.2': 'Nom complet',
    'register.3': 'Entrez votre nom complet',
    'register.4': 'Adresse e-mail',
    'register.5': 'Entrez votre e-mail',
    'register.6': "Nom d'utilisateur",
    'register.7': "Choisissez un nom d'utilisateur",
    'register.8': 'Mot de passe',
    'register.9': 'Créer un mot de passe',
    'register.9.1': 'Au moins 8 caractères',
    'register.9.2': 'Une majuscule',
    'register.9.3': 'Une minuscule',
    'register.9.4': 'Un chiffre',
    'register.9.5': 'Un caractère spécial',
    'register.10': 'Confirmer le mot de passe',
    'register.11': 'Confirmez votre mot de passe',
    'register.12': 'J\'accepte les Conditions d\'utilisation et la Politique de confidentialité',
    'register.13': 'Créer le compte',
    'register.14': 'Déjà un compte ?',
    'register.15': 'Se connecter',
    'register.16': 'Les mots de passe ne correspondent pas',
    'register.17': 'E-mail déjà enregistré',
    'register.18': "Nom d'utilisateur déjà pris",
    'register.19': 'Le mot de passe ne répond pas aux exigences',
}

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/fr/messages.json', 'r', encoding='utf-8') as f:
    fr = json.load(f)
fr.update(translations)
with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/fr/messages.json', 'w', encoding='utf-8') as f:
    json.dump(fr, f, ensure_ascii=False, indent=2)
print('Updated login and register sections')